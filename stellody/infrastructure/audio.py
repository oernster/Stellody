"""The audio engine: one feeder thread writing blocks into a WASAPI stream.

Blocking writes are what make this simple. The stream applies the back pressure,
so the feeder needs no clock of its own and no timing arithmetic: it reads a
block, writes it and blocks until the device has room, which is exactly the
pacing wanted. Nothing here schedules anything.

Each load builds a whole new session (reader, stream, thread) and stopping tears
that session down, so no state is shared between one track and the next and a
transport command can never reach a half replaced engine.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field

import numpy as np
import sounddevice

from stellody.domain.playback import (
    SILENT_VOLUME,
    UNITY_VOLUME,
    OutputReport,
    OutputRequest,
    PlaybackPosition,
    PlaybackState,
)
from stellody.domain.track import TrackSource
from stellody.infrastructure.decode import SourceReader
from stellody.infrastructure.wasapi import open_output

BLOCK_FRAMES = 4096
JOIN_TIMEOUT_SECONDS = 2.0


@dataclass(slots=True)
class _Session:
    """Everything one loaded track owns. Discarded whole when playback stops."""

    reader: SourceReader
    stream: sounddevice.OutputStream
    report: OutputReport
    dtype: str
    lock: threading.Lock = field(default_factory=threading.Lock)
    resume: threading.Event = field(default_factory=threading.Event)
    cancel: threading.Event = field(default_factory=threading.Event)
    finished: threading.Event = field(default_factory=threading.Event)
    thread: threading.Thread | None = None


class WasapiPlayback:
    """A PlaybackPort over sounddevice. The only class that touches a device.

    Volume is applied in software, so any level below unity is a deliberate
    alteration of the samples. At unity nothing multiplies the block at all,
    which is what lets an exclusive stream stay genuinely bit perfect.
    """

    def __init__(
        self, device: int | None = None, block_frames: int = BLOCK_FRAMES
    ) -> None:
        self._device = device
        self._block_frames = block_frames
        self._volume = UNITY_VOLUME
        self._session: _Session | None = None
        self._closed = False

    @property
    def state(self) -> PlaybackState:
        """Where the transport is right now."""
        session = self._session
        if session is None:
            return PlaybackState.STOPPED
        if session.resume.is_set() and not session.finished.is_set():
            return PlaybackState.PLAYING
        return PlaybackState.PAUSED

    @property
    def finished(self) -> bool:
        """Whether the loaded source has played all the way through."""
        session = self._session
        return session is not None and session.finished.is_set()

    @property
    def report(self) -> OutputReport | None:
        """What the open stream actually delivers; None when nothing is loaded."""
        session = self._session
        return None if session is None else session.report

    def load(self, source: TrackSource, request: OutputRequest) -> OutputReport:
        """Open `source` on a device and report what was actually opened."""
        self.stop()
        stream, report, dtype = open_output(request, self._device)
        try:
            reader = SourceReader(source, dtype=dtype)
        except Exception:
            stream.close()
            raise
        session = _Session(reader=reader, stream=stream, report=report, dtype=dtype)
        session.thread = threading.Thread(
            target=self._feed, args=(session,), name="stellody-feeder", daemon=True
        )
        self._session = session
        session.thread.start()
        return report

    def play(self) -> None:
        """Start or resume. Does nothing when no source is loaded."""
        session = self._session
        if session is None or session.finished.is_set():
            return
        session.stream.start()
        session.resume.set()

    def pause(self) -> None:
        """Hold position without releasing the device."""
        session = self._session
        if session is None:
            return
        session.resume.clear()
        session.stream.stop()

    def stop(self) -> None:
        """End playback and release the device."""
        session = self._session
        self._session = None
        if session is None:
            return
        session.cancel.set()
        session.resume.set()
        if session.thread is not None:
            session.thread.join(timeout=JOIN_TIMEOUT_SECONDS)
        session.stream.abort(ignore_errors=True)
        session.stream.close(ignore_errors=True)
        session.reader.close()

    def seek(self, frame: int) -> None:
        """Move to a frame offset within the loaded source, clamped to it."""
        session = self._session
        if session is None:
            return
        with session.lock:
            session.reader.seek(frame)
        session.finished.clear()

    @property
    def lead_frames(self) -> int:
        """One block: what has been handed to the device but not yet heard."""
        return self._block_frames

    def position(self) -> PlaybackPosition | None:
        """How far the DECODE has reached; None when nothing is loaded."""
        session = self._session
        if session is None:
            return None
        with session.lock:
            frame = session.reader.frame
            frame_count = session.reader.frame_count
            sample_rate = session.reader.sample_rate
        return PlaybackPosition(
            frame=frame, frame_count=frame_count, sample_rate=sample_rate
        )

    def set_volume(self, level: float) -> None:
        """Set output gain, where 0.0 is silence and 1.0 is unattenuated."""
        self._volume = min(max(SILENT_VOLUME, level), UNITY_VOLUME)

    def close(self) -> None:
        """Release every resource. The port is unusable afterwards."""
        self.stop()
        self._closed = True

    def _scaled(self, block: np.ndarray, dtype: str) -> np.ndarray:
        """The block at the current volume, untouched when that is unity."""
        if self._volume == UNITY_VOLUME:
            return block
        return (block * self._volume).astype(dtype)

    def _feed(self, session: _Session) -> None:
        """Read and write blocks until the track ends or the session is torn down."""
        while True:
            session.resume.wait()
            if session.cancel.is_set():
                return
            with session.lock:
                block = session.reader.read(self._block_frames)
            if len(block) == 0:
                session.finished.set()
                session.resume.clear()
                continue
            try:
                session.stream.write(self._scaled(block, session.dtype))
            except sounddevice.PortAudioError:
                session.finished.set()
                session.resume.clear()
