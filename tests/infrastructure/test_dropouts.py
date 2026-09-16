"""Every write that found the device's buffer already empty is written down.

Static heard while another program held every core is the report this exists
for. PortAudio's underflow answer was measured to say nothing on a shared
WASAPI stream, so the room in the buffer is what is read: a freshly started
stream has the whole buffer free, so a later write finding that much room
follows a device with nothing left to play.

The watch is held on its own with a clock it is told, then through the shipped
feeder with a stream whose buffer empties on the writes chosen for it. The
last test does it on the real device, which is the one that matters: the
first version of this passed against a fake and was blind on real hardware.
"""

from __future__ import annotations

import time

import numpy as np
import pytest
import soundfile

from stellody.domain.playback import OutputMode, OutputReport, OutputRequest
from stellody.domain.track import TrackSource
from stellody.infrastructure.audio import WasapiPlayback
from stellody.infrastructure.dropouts import DropoutWatch

RATE = 44100
BLOCK = 4096
CAPACITY = 1036
# Room as it was measured while writes kept up on a real shared stream.
KEEPING_UP = 300
# Where the fake clock says the feeder started reading, then shaping, then
# came back to write: away for 250 ms, 100 of them waiting to be run.
READ_FROM_SECONDS = 0.1
SHAPE_FROM_SECONDS = 0.2
AWAY_SECONDS = 0.25
# Longer than the device's whole queue, which buffering.py asks to be two
# blocks: about 195 ms on the machine this was measured on.
STARVE_SECONDS = 1.0
# How far past the audio it carried the fake clock says a write ran.
LATE_INSIDE_SECONDS = 0.09
# One steady write as measured on the real device: 60 frames of room before
# it, 107.3 ms to return.
MEASURED_ROOM = 60
MEASURED_WRITE_SECONDS = 0.1073
# Eight blocks of track, so the feeder writes a known number of times.
BLOCKS = 8
WAIT_SECONDS = 5.0
POLL_SECONDS = 0.01


class Clock:
    """A clock that says whatever it is told to."""

    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


class TestTheWatchOnItsOwn:
    def _watch(self, notes: list[str], clock: Clock) -> DropoutWatch:
        watch = DropoutWatch(notes.append, clock)
        watch.started(CAPACITY)
        return watch

    def test_a_buffer_with_something_in_it_says_nothing(self) -> None:
        notes: list[str] = []
        watch = self._watch(notes, Clock())
        for _ in range(3):
            watch.writing(KEEPING_UP, BLOCK, 0, RATE)
            watch.written()
        assert notes == []
        assert watch.count == 0

    def test_an_empty_buffer_is_noted_with_where_and_how_long_away(self) -> None:
        notes: list[str] = []
        clock = Clock()
        watch = self._watch(notes, clock)
        watch.writing(CAPACITY, BLOCK, 0, RATE)
        watch.written()
        clock.now = READ_FROM_SECONDS
        watch.reading()
        clock.now = SHAPE_FROM_SECONDS
        watch.shaping()
        clock.now = AWAY_SECONDS
        watch.writing(CAPACITY, BLOCK, RATE * 142, RATE)
        assert watch.count == 1
        assert "playback dropout 1 at 2:22" in notes[0]
        assert "23 ms buffer" in notes[0]
        assert f"{BLOCK} frames" in notes[0]
        assert "away 250 ms (100 ms reading, 50 ms shaping, 100 ms waiting" in notes[0]

    def test_a_write_that_took_longer_than_it_carried_held_a_silence(self) -> None:
        """The device cannot play faster than real time, so the difference
        between how long a write took and what it carried is a silence."""
        notes: list[str] = []
        clock = Clock()
        watch = self._watch(notes, clock)
        watch.writing(KEEPING_UP, BLOCK, 0, RATE)
        watch.written()
        clock.now = 1.0
        watch.writing(KEEPING_UP, BLOCK, RATE * 148, RATE)
        carried = (BLOCK + CAPACITY - KEEPING_UP) / RATE
        clock.now = 1.0 + carried + LATE_INSIDE_SECONDS
        watch.written()
        assert watch.count == 1
        assert "playback dropout 1 at 2:28" in notes[0]
        assert "ran dry for at least 90 ms inside a write" in notes[0]

    def test_a_write_that_kept_pace_holds_no_silence(self) -> None:
        """Measured on the real device: 107 ms for a write carrying 115 ms."""
        notes: list[str] = []
        clock = Clock()
        watch = self._watch(notes, clock)
        watch.writing(KEEPING_UP, BLOCK, 0, RATE)
        watch.written()
        clock.now = 1.0
        watch.writing(MEASURED_ROOM, BLOCK, 0, RATE)
        clock.now = 1.0 + MEASURED_WRITE_SECONDS
        watch.written()
        assert notes == []

    def test_the_first_write_after_a_start_is_not_a_dropout(self) -> None:
        """A started stream is empty by definition; so is one resumed."""
        notes: list[str] = []
        watch = self._watch(notes, Clock())
        watch.writing(CAPACITY, BLOCK, 0, RATE)
        watch.written()
        watch.started(CAPACITY)
        watch.writing(CAPACITY, BLOCK, 0, RATE)
        assert notes == []

    def test_a_stream_with_no_buffer_reading_is_never_drained(self) -> None:
        notes: list[str] = []
        watch = DropoutWatch(notes.append, Clock())
        watch.started(0)
        watch.writing(0, BLOCK, 0, RATE)
        watch.written()
        watch.writing(0, BLOCK, 0, RATE)
        assert notes == []


class EmptiesOnSome:
    """A stream whose buffer reads empty before the writes it is told to."""

    # Nothing queued, so the engine counts no buffer in its lead.
    latency = 0.0

    def __init__(self, empty_before: set[int]) -> None:
        self._empty_before = empty_before
        self._writes = 0

    @property
    def write_available(self) -> int:
        """The whole buffer at a start and before a chosen write; some else."""
        if self._writes == 0 or self._writes in self._empty_before:
            return CAPACITY
        return KEEPING_UP

    def start(self) -> None:
        """Nothing to start."""

    def stop(self) -> None:
        """Nothing to stop."""

    def write(self, block: np.ndarray) -> None:
        """Take the block."""
        self._writes += 1

    def abort(self, ignore_errors: bool = True) -> None:
        """Nothing held to abort."""

    def close(self, ignore_errors: bool = True) -> None:
        """Nothing held to release."""


def _opener(stream):
    """Hand back that stream, in `open_output`'s shape."""

    def open_it(request: OutputRequest, device: int | None):
        report = OutputReport(
            request=request,
            mode=OutputMode.SHARED,
            sample_rate=request.sample_rate,
            bit_depth=request.bit_depth,
        )
        return stream, report, "float32"

    return open_it


def _silent_track(tmp_path, frames: int) -> str:
    path = tmp_path / "silent.wav"
    soundfile.write(
        str(path), np.zeros((frames, 1), dtype="float32"), RATE, subtype="FLOAT"
    )
    return str(path)


def _played_through(player: WasapiPlayback) -> None:
    deadline = time.monotonic() + WAIT_SECONDS
    while not player.finished and time.monotonic() < deadline:
        time.sleep(POLL_SECONDS)
    assert player.finished


def test_the_feeder_notes_exactly_the_writes_that_found_it_empty(tmp_path) -> None:
    """Through the shipped feeder, so the reading is taken where it matters."""
    notes: list[str] = []
    empty_before = {2, 5}
    player = WasapiPlayback(
        block_frames=BLOCK,
        opener=_opener(EmptiesOnSome(empty_before)),
        dropouts=DropoutWatch(notes.append),
    )
    player.load(
        TrackSource(path=_silent_track(tmp_path, BLOCK * BLOCKS)),
        OutputRequest(RATE, 16),
    )
    try:
        player.play()
        _played_through(player)
        assert player.dropouts.count == len(empty_before)
        assert [note.split(" at ")[1].split(":")[0] for note in notes] == ["0", "0"]
    finally:
        player.stop()


def test_a_real_device_left_waiting_is_seen_to_run_dry(tmp_path) -> None:
    """On the machine's own output, starved on purpose, writing silence.

    The measurement the first version never took. Skipped where there is no
    output device to open, which is the only way a run can have nothing to say.
    """
    import sounddevice

    from stellody.infrastructure.output import open_output

    try:
        stream, _report, dtype = open_output(OutputRequest(RATE, 16), None)
    except Exception as error:  # noqa: BLE001 - no device is a skip, not a fault
        pytest.skip(f"no output device to open: {error}")
    notes: list[str] = []
    watch = DropoutWatch(notes.append)
    silence = np.zeros((BLOCK, stream.channels), dtype=dtype)
    try:
        stream.start()
        watch.started(stream.write_available)
        for _ in range(3):
            watch.writing(stream.write_available, BLOCK, 0, RATE)
            stream.write(silence)
            watch.written()
        time.sleep(STARVE_SECONDS)
        watch.writing(stream.write_available, BLOCK, 0, RATE)
        stream.write(silence)
    except sounddevice.PortAudioError as error:
        pytest.skip(f"the output device refused the probe: {error}")
    finally:
        stream.stop()
        stream.close()
    assert watch.count == 1, notes
