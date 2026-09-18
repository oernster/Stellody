"""Everything one loaded track owns, apart from the engine that drives it.

Split out of `audio.py` on 2026-09-18, when choosing the output device put
that file into the band below the length a module is allowed. The seam is the
one the engine's own docstring already draws: each load builds a whole new
session and stopping tears it down, so what a session holds and how it is let
go of is a concern of its own; the engine decides when.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field

import sounddevice

from stellody.domain.playback import OutputReport
from stellody.infrastructure.decode import AudioSource
from stellody.infrastructure.filtering import BiquadCascade

JOIN_TIMEOUT_SECONDS = 2.0


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
