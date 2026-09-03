"""The audio engine: one feeder thread writing blocks into a WASAPI stream.

Blocking writes are what make this simple. The stream applies the back pressure,
so the feeder needs no clock of its own and no timing arithmetic: it reads a
block, writes it and blocks until the device has room, which is exactly the
pacing wanted. Nothing here schedules anything.

Each load builds a whole new session (reader, stream, thread) and stopping tears
that session down, so no state is shared between one track and the next and a
transport command can never reach a half replaced engine.

A gapless transition is the one thing that crosses a track boundary without a
new session, because it has to: the only thing awake at the seam is the feeder
thread, halfway through a run of blocking writes. Nothing can be asked and
nothing can be loaded there, so the follower is opened while the current track
is still playing and the feeder reads straight on into it. The stream is never
stopped, so the device is handed one unbroken run of blocks.
"""

from __future__ import annotations

import threading
from collections.abc import Callable
from dataclasses import dataclass, field

import numpy as np
import sounddevice

from stellody.domain.equalising import Equalisation, cascade
from stellody.domain.playback import (
    SILENT_VOLUME,
    UNITY_VOLUME,
    OutputReport,
    OutputRequest,
    PlaybackPosition,
    PlaybackState,
)
from stellody.domain.spectrum import SILENT_BANDS
from stellody.domain.track import TrackSource
from stellody.infrastructure.analysing import BlockAnalyser
from stellody.infrastructure.decode import AudioSource, DecodeError, open_source
from stellody.infrastructure.filtering import BiquadCascade
from stellody.infrastructure.wasapi import open_output

BLOCK_FRAMES = 4096
JOIN_TIMEOUT_SECONDS = 2.0

# What open_output does, named so a test can hand in a stream of its own and
# read the samples the engine writes. Nothing else here opens a device.
Opener = Callable[
    [OutputRequest, int | None],
    tuple[sounddevice.OutputStream, OutputReport, str],
]


@dataclass(slots=True)
class _Session:
    """Everything one loaded track owns. Discarded whole when playback stops."""

    reader: AudioSource
    stream: sounddevice.OutputStream
    report: OutputReport
    dtype: str
    lock: threading.Lock = field(default_factory=threading.Lock)
    resume: threading.Event = field(default_factory=threading.Event)
    cancel: threading.Event = field(default_factory=threading.Event)
    finished: threading.Event = field(default_factory=threading.Event)
    thread: threading.Thread | None = None
    # Opened ahead of the seam so the feeder never has to wait at one.
    follower: AudioSource | None = None
    crossings: int = 0
    # The equalizer, designed for this stream's own sample rate. Empty
    # while it is flat, which is how it costs nothing.
    filtering: BiquadCascade = field(default_factory=BiquadCascade)


class WasapiPlayback:
    """A PlaybackPort over sounddevice. The only class that touches a device.

    Volume is applied in software, so any level below unity is a deliberate
    alteration of the samples. At unity nothing multiplies the block at all,
    which is what lets an exclusive stream stay genuinely bit perfect.
    """

    def __init__(
        self,
        device: int | None = None,
        block_frames: int = BLOCK_FRAMES,
        opener: Opener = open_output,
    ) -> None:
        self._device = device
        self._block_frames = block_frames
        self._opener = opener
        self._volume = UNITY_VOLUME
        self._equalisation = Equalisation()
        self._session: _Session | None = None
        self._closed = False
        # Off until something asks to see it, so a listener who never opens the
        # visualiser pays nothing at all for it. `_analyser` being None IS the
        # switch: there is no flag to disagree with it.
        self._analyser: BlockAnalyser | None = None
        self._visualising = False
        self._levels = SILENT_BANDS

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
        stream, report, dtype = self._opener(request, self._device)
        try:
            reader = open_source(source, dtype=dtype)
        except Exception:
            stream.close()
            raise
        session = _Session(
            reader=reader,
            stream=stream,
            report=report,
            dtype=dtype,
            filtering=self._designed_for(reader.sample_rate),
        )
        self._analyser = self._analyser_for(reader.sample_rate)
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
        if session.follower is not None:
            session.follower.close()

    def seek(self, frame: int) -> None:
        """Move to a frame offset within the loaded source, clamped to it."""
        session = self._session
        if session is None:
            return
        with session.lock:
            session.reader.seek(frame)
            session.filtering.reset()
        session.finished.clear()

    @property
    def crossings(self) -> int:
        """How many lined-up sources the feeder has run into by itself."""
        session = self._session
        if session is None:
            return 0
        with session.lock:
            return session.crossings

    def queue_next(self, source: TrackSource | None) -> bool:
        """Open what follows now, so the feeder never waits at the seam.

        A source whose shape the open stream cannot carry is refused rather
        than joined badly: the stream was opened for one rate and one channel
        count; writing anything else into it would be worse than the gap
        it was meant to avoid.
        """
        session = self._session
        if session is None:
            return False
        self._drop_follower(session)
        if source is None:
            return False
        try:
            candidate = open_source(source, dtype=session.dtype)
        except DecodeError:
            return False
        with session.lock:
            joins = (
                candidate.sample_rate == session.reader.sample_rate
                and candidate.channels == session.reader.channels
            )
            if joins:
                session.follower = candidate
        if not joins:
            candidate.close()
        return joins

    def _drop_follower(self, session: _Session) -> None:
        """Let go of whatever was lined up, closing its file."""
        with session.lock:
            previous = session.follower
            session.follower = None
        if previous is not None:
            previous.close()

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

    def _designed_for(self, sample_rate: int) -> BiquadCascade:
        """The equalizer as this sample rate needs it to be designed."""
        return BiquadCascade(cascade(self._equalisation, sample_rate))

    def set_equalisation(self, equalisation: Equalisation) -> None:
        """Set the curve, redesigning it for whatever is open right now.

        The coefficients depend on the sample rate, so they cannot be
        worked out until a stream is open; the curve is kept here so that
        one chosen before anything is loaded still applies to whatever is
        loaded next, exactly as the volume does.
        """
        self._equalisation = equalisation
        session = self._session
        if session is None:
            return
        with session.lock:
            session.filtering = self._designed_for(session.reader.sample_rate)

    def _analyser_for(self, sample_rate: int) -> BlockAnalyser | None:
        """One analyser per stream, since its bands depend on the sample rate."""
        if not self._visualising:
            return None
        return BlockAnalyser(sample_rate, self._block_frames)

    def _measure(self, shaped: np.ndarray) -> None:
        """Read the block that has just gone out, if anybody is watching.

        After the write, so this can never be what delays a device. What is
        measured is the block AFTER the equalizer and BEFORE the volume: the
        equalizer is what the bands are named for, while volume scales every
        band by the same amount and so says nothing about the music. A display
        that shrank when the volume came down would report the knob, not the
        record.

        The answer is swapped in as one whole tuple. The reader is the
        interface thread and a swap is a single rebinding, so what it reads is
        either the last measurement or this one, never half of each; a lock
        here would be the feeder waiting on a painter, which is exactly what
        this must never do.
        """
        analyser = self._analyser
        if analyser is None:
            return
        measured = analyser.measure(shaped)
        if measured is not None:
            self._levels = measured

    @property
    def levels(self) -> tuple[float, ...]:
        """The bands as they were last measured; silence when nothing is on."""
        return self._levels

    def set_visualising(self, on: bool) -> None:
        """Start or stop measuring what goes out.

        Stopping forgets the last measurement as well as the analyser, so a
        display turned back on opens empty rather than showing the bands of
        whatever was playing when it was last switched off.
        """
        self._visualising = on
        session = self._session
        rate = None if session is None else session.reader.sample_rate
        self._analyser = None if rate is None else self._analyser_for(rate)
        if not on:
            self._levels = SILENT_BANDS

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
                if len(block) == 0 and session.follower is not None:
                    # The seam. No stop, no reopen and no silence written:
                    # the very next write carries the following track.
                    session.reader.close()
                    session.reader = session.follower
                    session.follower = None
                    session.crossings += 1
                    block = session.reader.read(self._block_frames)
                filtering = session.filtering
            if len(block) == 0:
                session.finished.set()
                session.resume.clear()
                continue
            try:
                shaped = filtering.process(block)
                session.stream.write(self._scaled(shaped, session.dtype))
                self._measure(shaped)
            except sounddevice.PortAudioError:
                # A write that fails while nothing is meant to be playing is a
                # pause landing on this thread, not a track ending. `pause`
                # clears the resume before it stops the stream, so a feeder
                # already past its wait writes into a stream that has just
                # been stopped and PortAudio refuses it. Calling that an
                # ending is what made a paused track unresumable: `play`
                # declines to start a finished session, so the press did
                # nothing. The poll then gave the device back, which left the
                # press after it reloading the track from its beginning.
                # The block in hand is dropped rather than kept, being the one
                # the device was refusing anyway.
                if not session.resume.is_set():
                    continue
                session.finished.set()
                session.resume.clear()
