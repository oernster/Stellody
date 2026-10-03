"""Everything one loaded track owns, apart from the engine that drives it.

Split out of `audio.py` on 2026-09-18, when choosing the output device put
that file into the band below the length a module is allowed. The seam is the
one the engine's own docstring already draws: each load builds a whole new
session and stopping tears it down, so what a session holds and how it is let
go of is a concern of its own; the engine decides when.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field, replace

import numpy as np
import sounddevice

from stellody.domain.playback import OutputReport
from stellody.domain.track import TrackSource
from stellody.infrastructure.decode import (
    AudioSource,
    DecodeError,
    is_integer,
    open_source,
)
from stellody.infrastructure.filtering import BiquadCascade

JOIN_TIMEOUT_SECONDS = 2.0
# One channel is a mono recording, which every speaker plays.
MONO = 1
NO_PLACE = (
    "cannot play {path}: it carries {carried} channels "
    "and the output was opened for {channels}"
)


def opened_to_fit(source: TrackSource, dtype: str, channels: int) -> AudioSource:
    """Open `source` for a stream of `channels`; refuse one it cannot carry.

    Found by the audit of 2026-10-03: every stream is opened for two
    channels, so a mono file's first write was refused by sounddevice and the
    feeder died behind a track still claiming to play. A mono file is taken
    and spread across the stream (`Session.fitted`). Any other count the
    stream was not opened for is refused here, naming both counts, because
    the stream has to be open before the file can be read and a stream for
    six channels is one few devices will open.
    """
    reader = open_source(source, dtype=dtype)
    if reader.channels in (MONO, channels):
        return reader
    reader.close()
    raise DecodeError(
        NO_PLACE.format(path=source.path, carried=reader.channels, channels=channels)
    )


def as_delivered(report: OutputReport, reader: AudioSource, dtype: str) -> OutputReport:
    """The report, no longer exact where a float source meets an integer stream.

    The reader converts such a file itself, scaled and clipped (`decode.py`),
    which is sound rather than silence but is not the file's own samples.
    """
    if reader.floating and is_integer(dtype):
        return replace(report, samples_exact=False)
    return report


@dataclass(slots=True)
class Session:
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
    # What the device keeps queued, as the stream reports it: heard that much
    # after it is written. See buffering.py.
    buffer_frames: int = 0
    # The room a fresh start showed: the whole buffer, before anything queued.
    capacity: int | None = None
    # Whether a write failed while playing, which is the device going away:
    # the stream cannot be resumed, only opened again.
    interrupted: bool = False
    # Why the feeder stopped when nothing it expected went wrong; empty
    # until then. The feeder has ended by the time this is set.
    failure: str = ""

    def fitted(self, block: np.ndarray) -> np.ndarray:
        """The block across every channel of the stream; mono on each of them."""
        channels = self.report.request.channels
        if block.shape[1] == channels:
            return block
        return np.repeat(block, channels, axis=1)

    def joins(self, candidate: AudioSource) -> bool:
        """Whether `candidate` can run on in this stream under this report.

        The rate and the channel count are what the stream can carry. The
        rest is what the report says: found by the audit of 2026-10-03, a
        follower inherits the report of the track it follows, so one stating
        another depth (nought for a lossy file) or holding another kind of
        sample would play under a claim that is not true of it. Such a
        follower opens on its own instead, with a report of its own.
        Called with the lock held, since the reader may be swapped beneath it.
        """
        current = self.reader
        return (
            candidate.sample_rate == current.sample_rate
            and candidate.channels == current.channels
            and candidate.bit_depth == current.bit_depth
            and candidate.floating == current.floating
        )

    def drop_follower(self) -> None:
        """Let go of whatever was lined up, closing its file."""
        with self.lock:
            previous = self.follower
            self.follower = None
        if previous is not None:
            previous.close()

    def end(self) -> None:
        """Stop the feeder, then release the stream and every file held."""
        self.cancel.set()
        self.resume.set()
        if self.thread is not None:
            self.thread.join(timeout=JOIN_TIMEOUT_SECONDS)
        self.stream.abort(ignore_errors=True)
        self.stream.close(ignore_errors=True)
        self.reader.close()
        if self.follower is not None:
            self.follower.close()
