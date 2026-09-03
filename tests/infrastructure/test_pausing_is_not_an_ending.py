"""Pausing must leave the track resumable, whatever the device says about it.

Reported against a real library: starting a track, pausing it and pressing play
again began the track from its beginning instead of carrying on.

`pause` clears the resume and then stops the stream, so a feeder already past
its wait writes into a stream that has just been stopped. PortAudio refuses
that write; the failure used to be read as the track ending. `play`
declines to start a finished session, so the press did nothing at all; the poll
a quarter of a second later then treated the ending as real and gave the device
back, which is what left the press after it reloading the track from nothing.

The stream here refuses a write once it has been stopped, which is what a real
one does. Nothing else in this file is a stand-in: the reader, the feeder and
the session are the shipped ones.
"""

from __future__ import annotations

import time

import numpy as np
import sounddevice
import soundfile

from stellody.domain.playback import (
    OutputMode,
    OutputReport,
    OutputRequest,
    PlaybackState,
)
from stellody.domain.track import TrackSource
from stellody.infrastructure.audio import WasapiPlayback

RATE = 44100
SECONDS = 20
SETTLE = 0.4


class StoppedStreamRefuses:
    """A stream that refuses a write once stopped, as PortAudio does."""

    def __init__(self) -> None:
        self.blocks: list[np.ndarray] = []
        self.running = False

    def start(self) -> None:
        """Accept writes again."""
        self.running = True

    def stop(self) -> None:
        """Refuse writes from here until started again."""
        self.running = False

    def write(self, block: np.ndarray) -> None:
        """Play in real time; refuse a write the stop landed in the middle of.

        A real blocking write holds the thread for the length of the block, so
        a pause arriving during one stops the stream underneath it. That write
        is the one that raises, which is the whole point of this file: the
        failure is a pause landing on the feeder rather than a track ending.
        """
        if not self.running:
            raise sounddevice.PortAudioError("Stream is stopped")
        time.sleep(block.shape[0] / RATE)
        if not self.running:
            raise sounddevice.PortAudioError("Stream stopped during the write")
        self.blocks.append(np.array(block, copy=True))

    def abort(self, ignore_errors: bool = True) -> None:
        """Nothing held to abort."""

    def close(self, ignore_errors: bool = True) -> None:
        """Nothing held to release."""


def _opener(stream: StoppedStreamRefuses):
    """An opener handing back that stream, in `open_output`'s shape."""

    def open_it(request: OutputRequest, device: int | None):
        report = OutputReport(
            request=request,
            mode=OutputMode.SHARED,
            sample_rate=request.sample_rate,
            bit_depth=request.bit_depth,
        )
        return stream, report, "float32"

    return open_it


def _long_track(tmp_path) -> str:
    """A file long enough that a pause partway cannot be its ending."""
    path = tmp_path / "long.wav"
    samples = np.zeros((RATE * SECONDS, 1), dtype="float32")
    soundfile.write(str(path), samples, RATE, subtype="FLOAT")
    return str(path)


def _paused_partway(tmp_path):
    """A player started on that track, then paused by the listener."""
    stream = StoppedStreamRefuses()
    player = WasapiPlayback(opener=_opener(stream))
    player.load(TrackSource(path=_long_track(tmp_path)), OutputRequest(RATE, 16))
    player.play()
    time.sleep(SETTLE)
    player.pause()
    time.sleep(SETTLE)
    return player


class TestAPauseLandingOnTheFeeder:
    def test_the_track_is_not_reported_as_finished(self, tmp_path) -> None:
        """The whole of what this is for."""
        player = _paused_partway(tmp_path)
        try:
            assert player.finished is False
        finally:
            player.stop()

    def test_it_reads_as_paused(self, tmp_path) -> None:
        """A held track is a paused one, whatever the write did."""
        player = _paused_partway(tmp_path)
        try:
            assert player.state is PlaybackState.PAUSED
        finally:
            player.stop()

    def test_pressing_play_resumes(self, tmp_path) -> None:
        """`play` declines a finished session, so this is what broke."""
        player = _paused_partway(tmp_path)
        try:
            player.play()
            time.sleep(SETTLE)
            assert player.state is PlaybackState.PLAYING
        finally:
            player.stop()

    def test_it_carries_on_from_where_it_was(self, tmp_path) -> None:
        """The reported symptom: it must not begin the track again."""
        player = _paused_partway(tmp_path)
        try:
            held = player.position().frame
            assert held > 0, "the probe paused before anything played"
            player.play()
            time.sleep(SETTLE)
            assert player.position().frame > held
        finally:
            player.stop()
