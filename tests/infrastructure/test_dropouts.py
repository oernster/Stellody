"""Every write that found the device already empty is written down.

Static heard while another program held every core is the report this exists
for. PortAudio answers underflowed from a write whose device ran dry; these
tests hold that the answer is counted and put into words, both in the watch on
its own and through the shipped feeder with a stream that says so.
"""

from __future__ import annotations

import time

import numpy as np
import soundfile

from stellody.domain.playback import OutputMode, OutputReport, OutputRequest
from stellody.domain.track import TrackSource
from stellody.infrastructure.audio import WasapiPlayback
from stellody.infrastructure.dropouts import DropoutWatch

RATE = 44100
BLOCK = 4096
# A quarter of a second of track: a few blocks, over in no time at all.
TRACK_FRAMES = RATE // 4
# How late the fake clock says the late write was.
LATE_SECONDS = 0.25
WAIT_SECONDS = 5.0
POLL_SECONDS = 0.01


class Clock:
    """A clock that says whatever it is told to."""

    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


class TestTheWatchOnItsOwn:
    def test_a_write_that_kept_up_says_nothing(self) -> None:
        notes: list[str] = []
        watch = DropoutWatch(notes.append, Clock())
        watch.wrote(False, BLOCK, RATE)
        watch.wrote(False, BLOCK, RATE)
        assert notes == []
        assert watch.count == 0

    def test_a_dry_device_is_counted_with_how_late_the_write_was(self) -> None:
        notes: list[str] = []
        clock = Clock()
        watch = DropoutWatch(notes.append, clock)
        watch.wrote(False, BLOCK, RATE)
        clock.now = LATE_SECONDS
        watch.wrote(True, BLOCK, RATE)
        assert watch.count == 1
        assert len(notes) == 1
        assert "playback dropout 1" in notes[0]
        assert f"{BLOCK} frames" in notes[0]
        assert "250 ms since the write before" in notes[0]

    def test_a_start_is_not_reported_as_a_late_write(self) -> None:
        """A pause is a long gap between writes that nobody should read as a
        starved feeder, so starting again forgets the write before it."""
        notes: list[str] = []
        clock = Clock()
        watch = DropoutWatch(notes.append, clock)
        watch.wrote(False, BLOCK, RATE)
        clock.now = LATE_SECONDS
        watch.started()
        watch.wrote(True, BLOCK, RATE)
        assert "the first write" in notes[0]

    def test_it_can_be_built_with_nowhere_to_write(self) -> None:
        """The engine's default: counted, said to nobody, never a failure."""
        watch = DropoutWatch()
        watch.wrote(True, BLOCK, RATE)
        assert watch.count == 1


class DryStream:
    """A stream whose device has always run dry by the time a block arrives."""

    def start(self) -> None:
        """Nothing to start."""

    def stop(self) -> None:
        """Nothing to stop."""

    def write(self, block: np.ndarray) -> bool:
        """Take the block and say the device was already empty."""
        return True

    def abort(self, ignore_errors: bool = True) -> None:
        """Nothing held to abort."""

    def close(self, ignore_errors: bool = True) -> None:
        """Nothing held to release."""


def _opener(request: OutputRequest, device: int | None):
    """Hand back the dry stream, in `open_output`'s shape."""
    report = OutputReport(
        request=request,
        mode=OutputMode.SHARED,
        sample_rate=request.sample_rate,
        bit_depth=request.bit_depth,
    )
    return DryStream(), report, "float32"


def test_the_feeder_hands_every_dry_write_to_the_watch(tmp_path) -> None:
    """Through the shipped feeder, so the answer is not dropped on the way."""
    path = tmp_path / "short.wav"
    samples = np.zeros((TRACK_FRAMES, 1), dtype="float32")
    soundfile.write(str(path), samples, RATE, subtype="FLOAT")
    notes: list[str] = []
    player = WasapiPlayback(
        block_frames=BLOCK, opener=_opener, dropouts=DropoutWatch(notes.append)
    )
    player.load(TrackSource(path=str(path)), OutputRequest(RATE, 16))
    try:
        player.play()
        deadline = time.monotonic() + WAIT_SECONDS
        while not player.finished and time.monotonic() < deadline:
            time.sleep(POLL_SECONDS)
        assert player.finished
        blocks = -(-TRACK_FRAMES // BLOCK)
        assert player.dropouts.count == blocks
        assert len(notes) == blocks
    finally:
        player.stop()
