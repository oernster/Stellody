"""A stand-in device that refuses what a real one refuses.

Shared by the tests that drive the engine with files whose shape or sample
format differs from the stream's. The other engine tests write into streams
that accept anything, which is exactly what hid a mono file playing silence:
sounddevice checks every write against the stream it was opened as and raises
when the channel count or the sample type differs. This stream repeats those
checks, so a block the real device would refuse is refused here too.

Nothing is mocked. The stream is hand written, the files are generated in the
test's own folder and the decode is the real one.
"""

from __future__ import annotations

import time

import numpy as np
import sounddevice

from stellody.domain.playback import OutputMode, OutputReport, OutputRequest
from stellody.infrastructure.audio import WasapiPlayback

SETTLE_SECONDS = 5.0
POLL_SECONDS = 0.01
# Where every probing open is pointed; the stand-ins never look at it.
A_DEVICE = 0


class CheckingStream:
    """A stream that keeps what it is written and refuses a wrong shape."""

    # No buffer to speak of, so the dropout watch never reads it as drained.
    write_available = 0
    # Nothing queued, so the engine counts no buffer in its lead.
    latency = 0.0

    def __init__(self, channels: int, dtype: str) -> None:
        self.channels = channels
        self.dtype = dtype
        self.blocks: list[np.ndarray] = []
        self.closed = False

    def start(self) -> None:
        """Nothing to start."""

    def stop(self, ignore_errors: bool = True) -> None:
        """Nothing to stop."""

    def abort(self, ignore_errors: bool = True) -> None:
        """Nothing to abort; the engine calls this when it stops."""

    def close(self, ignore_errors: bool = True) -> None:
        """Record that the device was given back."""
        self.closed = True

    def write(self, block: np.ndarray) -> None:
        """Keep a copy, after the checks sounddevice makes of every write."""
        if block.shape[1] != self.channels:
            raise ValueError("number of channels must match")
        if block.dtype != np.dtype(self.dtype):
            raise TypeError("dtype mismatch")
        self.blocks.append(np.array(block, copy=True))

    @property
    def written(self) -> np.ndarray:
        """Everything handed to the device, as one run of frames."""
        if not self.blocks:
            return np.zeros((0, self.channels), dtype=self.dtype)
        return np.concatenate(self.blocks, axis=0)


class FailingStream(CheckingStream):
    """A stream whose every write fails in a way nothing expected."""

    def write(self, block: np.ndarray) -> None:
        """Fail as no device error does."""
        raise ZeroDivisionError("a fault nobody planned for")


def mixer_opener(streams: list[CheckingStream], kind: type = CheckingStream):
    """An opener in open_output's shape, opening a mixer stream each time."""

    def open_it(request: OutputRequest, _device: object):
        stream = kind(request.channels, "float32")
        streams.append(stream)
        report = OutputReport(
            request=request,
            mode=OutputMode.SHARED,
            sample_rate=request.sample_rate,
            bit_depth=32,
        )
        return stream, report, "float32"

    return open_it


def stand_in_device(monkeypatch, streams: list[CheckingStream], takes: tuple[str, ...]):
    """Put a device in front of the real WASAPI module, taking these types.

    `takes` is what the device accepts exclusively. The reference machine's
    onboard device takes 16 bit alone, which is the case the audit measured.
    """

    def check(device=None, samplerate=None, channels=None, dtype=None, **_settings):
        if dtype not in takes:
            raise sounddevice.PortAudioError("format not supported")

    def opened(device=None, samplerate=None, channels=None, dtype=None, **_settings):
        stream = CheckingStream(channels, dtype)
        streams.append(stream)
        return stream

    monkeypatch.setattr(sounddevice, "check_output_settings", check)
    monkeypatch.setattr(sounddevice, "OutputStream", opened)


def play_out(player: WasapiPlayback) -> None:
    """Let the feeder run until it reports the whole thing has played."""
    deadline = time.monotonic() + SETTLE_SECONDS
    while time.monotonic() < deadline:
        if player.finished:
            return
        time.sleep(POLL_SECONDS)
    raise AssertionError("the engine never reported that it had finished")


def settle(player: WasapiPlayback) -> None:
    """Wait until the feeder has stopped of its own accord."""
    deadline = time.monotonic() + SETTLE_SECONDS
    while time.monotonic() < deadline:
        thread = player._session.thread if player._session else None
        if thread is None or not thread.is_alive():
            return
        time.sleep(POLL_SECONDS)
    raise AssertionError("the feeder never stopped")
