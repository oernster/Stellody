"""The device keeps two blocks queued; the position is put back by that much.

A 23 ms queue was measured running dry thirty times in sixteen seconds while a
Nuitka build held every core. The first test opens the machine's real output
through the shipped opener and requires the queue it gets to hold the two
blocks asked for, since what the host grants is the only answer that matters.
The second holds the engine to counting that queue in its lead, so the clock
and the pictures are not ahead of the speakers by the whole of it.
"""

from __future__ import annotations

import numpy as np
import pytest
import soundfile

from stellody.domain.playback import OutputMode, OutputReport, OutputRequest
from stellody.domain.track import TrackSource
from stellody.infrastructure.audio import WasapiPlayback
from stellody.infrastructure.buffering import (
    BLOCK_FRAMES,
    BUFFER_BLOCKS,
    buffer_seconds,
)

RATE = 44100
# What the fake stream says it keeps queued.
QUEUED_SECONDS = 0.2


def test_the_real_device_grants_a_queue_of_two_blocks() -> None:
    """Skipped only where there is no output device to open at all."""
    import sounddevice

    from stellody.infrastructure.output import open_output

    try:
        stream, _report, _dtype = open_output(OutputRequest(RATE, 16), None)
    except Exception as error:  # noqa: BLE001 - no device is a skip, not a fault
        pytest.skip(f"no output device to open: {error}")
    try:
        stream.start()
        room = stream.write_available
    except sounddevice.PortAudioError as error:
        pytest.skip(f"the output device refused the probe: {error}")
    finally:
        stream.stop()
        stream.close()
    assert room >= BUFFER_BLOCKS * BLOCK_FRAMES


def test_the_queue_asked_for_is_two_blocks_at_the_stream_rate() -> None:
    assert buffer_seconds(RATE) == BUFFER_BLOCKS * BLOCK_FRAMES / RATE


class Queued:
    """A stream that says it keeps a fixed amount queued; takes every write."""

    latency = QUEUED_SECONDS
    write_available = 0

    def start(self) -> None:
        """Nothing to start."""

    def stop(self) -> None:
        """Nothing to stop."""

    def write(self, block: np.ndarray) -> None:
        """Take the block."""

    def abort(self, ignore_errors: bool = True) -> None:
        """Nothing held to abort."""

    def close(self, ignore_errors: bool = True) -> None:
        """Nothing held to release."""


def _opener(request: OutputRequest, device: int | None):
    report = OutputReport(
        request=request,
        mode=OutputMode.SHARED,
        sample_rate=request.sample_rate,
        bit_depth=request.bit_depth,
    )
    return Queued(), report, "float32"


def test_the_lead_counts_the_queue_as_well_as_the_block(tmp_path) -> None:
    path = tmp_path / "silent.wav"
    soundfile.write(
        str(path), np.zeros((RATE, 1), dtype="float32"), RATE, subtype="FLOAT"
    )
    player = WasapiPlayback(opener=_opener)
    assert player.lead_frames == BLOCK_FRAMES, "nothing loaded, nothing queued"
    player.load(TrackSource(path=str(path)), OutputRequest(RATE, 16))
    try:
        assert player.lead_frames == BLOCK_FRAMES + round(QUEUED_SECONDS * RATE)
    finally:
        player.stop()
