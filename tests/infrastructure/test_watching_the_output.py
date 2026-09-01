"""The visualiser measured against the engine itself, not against a stand-in.

Three claims the milestone makes, each held here by playing real audio through
the real engine into a stand-in device, which is the same arrangement the seam
tests use: only the device is stood in for, because a device would make a noise
in a test run and a silent one would prove nothing.

The hardest of the three is the first. A display that altered a sample would
break the bit perfect claim silently; nobody would hear it until they went
looking, so what is compared is every frame written with the display on against
every frame written with it off.
"""

from __future__ import annotations

import time

import numpy as np
import pytest
import soundfile

from stellody.domain.playback import OutputMode, OutputReport, OutputRequest
from stellody.domain.spectrum import SILENT_BANDS
from stellody.domain.track import TrackSource
from stellody.infrastructure.audio import WasapiPlayback

RATE = 44100
DEPTH = 32
# Several blocks' worth, so the feeder measures more than once and the last
# short block is not the only thing the display ever sees.
FRAMES = 20000
TONE_HZ = 1000.0
SETTLE_SECONDS = 5.0
POLL_SECONDS = 0.01


class RecordingStream:
    """A stream that keeps what it was written instead of playing it."""

    def __init__(self) -> None:
        self.blocks: list[np.ndarray] = []
        self.closed = False

    def start(self) -> None:
        """Nothing to start."""

    def stop(self) -> None:
        """Nothing to stop."""

    def write(self, block: np.ndarray) -> None:
        """Keep a copy, since the engine reuses the array it hands over."""
        self.blocks.append(np.array(block, copy=True))

    def abort(self, ignore_errors: bool = True) -> None:
        """Nothing to abort."""

    def close(self, ignore_errors: bool = True) -> None:
        """Record that the device was given back."""
        self.closed = True

    @property
    def written(self) -> np.ndarray:
        """Everything handed to the device, as one run of frames."""
        if not self.blocks:
            return np.zeros((0, 1), dtype="float32")
        return np.concatenate(self.blocks, axis=0)


def _opener(stream: RecordingStream):
    """An opener handing back the recording stream, in open_output's shape."""

    def open_it(request: OutputRequest, device: int | None):
        report = OutputReport(
            request=request,
            mode=OutputMode.SHARED,
            sample_rate=request.sample_rate,
            bit_depth=request.bit_depth,
        )
        return stream, report, "float32"

    return open_it


def _tone_file(tmp_path, name: str) -> str:
    """A file of real content, so the bands have something to report."""
    steps = np.arange(FRAMES, dtype="float32") / RATE
    samples = np.sin(2 * np.pi * TONE_HZ * steps).reshape(-1, 1)
    path = tmp_path / name
    soundfile.write(str(path), samples, RATE, subtype="FLOAT")
    return str(path)


def _played(path: str, watching: bool) -> tuple[np.ndarray, tuple[float, ...]]:
    """Play the whole file, watching or not; what went out and what was seen."""
    stream = RecordingStream()
    player = WasapiPlayback(opener=_opener(stream))
    player.set_visualising(watching)
    player.load(
        TrackSource(path=path), OutputRequest(sample_rate=RATE, bit_depth=DEPTH)
    )
    player.play()
    deadline = time.monotonic() + SETTLE_SECONDS
    while time.monotonic() < deadline and not player.finished:
        time.sleep(POLL_SECONDS)
    assert player.finished, "the engine never reported that it had finished"
    seen = player.levels
    player.stop()
    return stream.written, seen


@pytest.fixture
def tone(tmp_path) -> str:
    """One file of a steady tone, played by every test here."""
    return _tone_file(tmp_path, "tone.wav")


def test_watching_changes_not_one_sample_of_what_goes_out(tone) -> None:
    """The bit perfect claim, measured rather than reasoned about.

    Every frame written with the display on, against every frame written with
    it off. The measurement reads the block after the device has been handed
    it, so there is nothing for it to change even in principle; this is what
    turns that into something that would fail if it stopped being true.
    """
    quiet, _ = _played(tone, watching=False)
    watched, _ = _played(tone, watching=True)

    assert watched.shape == quiet.shape, "a frame was inserted or dropped"
    assert np.array_equal(watched, quiet), "watching altered the audio"


def test_nothing_is_measured_when_nobody_is_watching(tone) -> None:
    """Off costs nothing rather than little, which is the whole bargain."""
    _, seen = _played(tone, watching=False)
    assert seen == SILENT_BANDS


def test_a_tone_reaches_the_display_through_the_whole_engine(tone) -> None:
    """End to end: a real file decoded, fed, written and measured."""
    _, seen = _played(tone, watching=True)
    assert seen != SILENT_BANDS, "the display saw nothing at all"
    assert max(seen) > 0.5, "a full scale tone should reach well up the strip"


def test_turning_it_off_forgets_what_was_last_seen(tone) -> None:
    """Otherwise a display turned back on opens showing an old record."""
    stream = RecordingStream()
    player = WasapiPlayback(opener=_opener(stream))
    player.set_visualising(True)
    player.load(
        TrackSource(path=tone), OutputRequest(sample_rate=RATE, bit_depth=DEPTH)
    )
    player.play()
    deadline = time.monotonic() + SETTLE_SECONDS
    while time.monotonic() < deadline and not player.finished:
        time.sleep(POLL_SECONDS)
    assert player.levels != SILENT_BANDS

    player.set_visualising(False)

    assert player.levels == SILENT_BANDS
    player.stop()


def test_asking_to_watch_before_anything_is_loaded_is_remembered(tone) -> None:
    """A listener turns the strip on while the library is still idle."""
    stream = RecordingStream()
    player = WasapiPlayback(opener=_opener(stream))
    player.set_visualising(True)
    assert player.levels == SILENT_BANDS, "nothing has played, so nothing was seen"

    player.load(
        TrackSource(path=tone), OutputRequest(sample_rate=RATE, bit_depth=DEPTH)
    )
    player.play()
    deadline = time.monotonic() + SETTLE_SECONDS
    while time.monotonic() < deadline and not player.finished:
        time.sleep(POLL_SECONDS)

    assert player.levels != SILENT_BANDS, "the choice was forgotten by the load"
    player.stop()
