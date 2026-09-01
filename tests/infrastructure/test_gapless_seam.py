"""Measuring the seam between two tracks, sample by sample.

The milestone this belongs to asks for the join to be measured rather than
judged by a listener, so that is what happens here: two files of known samples
are played through the engine with a stand-in stream recording every block it
is handed, then the recording is compared against the two files laid end to
end. Anything the engine inserted, dropped or reordered at the boundary shows
up as an inequality rather than as an opinion.

The stream is hand written rather than mocked; the decode is of real
files: only the device is stood in for, because a device would make a noise in
a test run and a silent one would prove nothing.
"""

from __future__ import annotations

import time

import numpy as np
import pytest
import soundfile

from stellody.domain.playback import OutputMode, OutputReport, OutputRequest
from stellody.domain.track import TrackSource
from stellody.infrastructure.audio import WasapiPlayback

RATE = 44100
DEPTH = 32
# Deliberately not a whole number of blocks, so the first track ends part way
# through one and the seam falls inside a write rather than tidily between two.
FIRST_FRAMES = 10000
SECOND_FRAMES = 6000
SETTLE_SECONDS = 5.0
POLL_SECONDS = 0.01


class RecordingStream:
    """A stream that keeps what it was written instead of playing it."""

    def __init__(self) -> None:
        self.blocks: list[np.ndarray] = []
        self.starts = 0
        self.stops = 0
        self.closed = False

    def start(self) -> None:
        """Count the start, so a restart across the seam would be visible."""
        self.starts += 1

    def stop(self) -> None:
        """Count the stop, for the same reason."""
        self.stops += 1

    def write(self, block: np.ndarray) -> None:
        """Keep a copy, since the engine reuses the array it hands over."""
        self.blocks.append(np.array(block, copy=True))

    def abort(self, ignore_errors: bool = True) -> None:
        """Nothing to abort; the engine calls this when it stops."""

    def close(self, ignore_errors: bool = True) -> None:
        """Record that the device was given back."""
        self.closed = True

    @property
    def written(self) -> np.ndarray:
        """Everything handed to the device, as one run of frames."""
        if not self.blocks:
            return np.zeros((0, 1), dtype="float32")
        return np.concatenate(self.blocks, axis=0)


def _ramp(frames: int, start: float) -> np.ndarray:
    """A run of distinct samples, so a dropped frame cannot hide in silence."""
    return (start + np.arange(frames, dtype="float32") / 100000.0).reshape(-1, 1)


def _written(tmp_path, name: str, samples: np.ndarray, rate: int = RATE) -> str:
    """One float WAV holding exactly these samples, so they read back exact."""
    path = tmp_path / name
    soundfile.write(str(path), samples, rate, subtype="FLOAT")
    return str(path)


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


def _play_out(player: WasapiPlayback) -> None:
    """Let the feeder run until it reports the whole thing has played."""
    deadline = time.monotonic() + SETTLE_SECONDS
    while time.monotonic() < deadline:
        if player.finished:
            return
        time.sleep(POLL_SECONDS)
    raise AssertionError("the engine never reported that it had finished")


@pytest.fixture
def stream() -> RecordingStream:
    """The stand-in device every test here plays into."""
    return RecordingStream()


def test_the_seam_carries_every_frame_of_both_tracks_and_nothing_else(
    tmp_path, stream: RecordingStream
) -> None:
    """The measurement this milestone asks for: the join, sample by sample."""
    first = _ramp(FIRST_FRAMES, 0.0)
    second = _ramp(SECOND_FRAMES, 0.5)
    one = _written(tmp_path, "one.wav", first)
    two = _written(tmp_path, "two.wav", second)

    player = WasapiPlayback(opener=_opener(stream))
    player.load(TrackSource(path=one), OutputRequest(sample_rate=RATE, bit_depth=DEPTH))
    assert player.queue_next(TrackSource(path=two)) is True
    player.play()
    _play_out(player)
    player.stop()

    expected = np.concatenate([first, second], axis=0)
    written = stream.written
    assert written.shape == expected.shape, "a frame was inserted or dropped"
    assert np.array_equal(written, expected), "the samples are not the two tracks"


def test_the_device_is_never_restarted_across_the_seam(
    tmp_path, stream: RecordingStream
) -> None:
    """Reopening is the other half of the gap; it must not happen either."""
    one = _written(tmp_path, "one.wav", _ramp(FIRST_FRAMES, 0.0))
    two = _written(tmp_path, "two.wav", _ramp(SECOND_FRAMES, 0.5))

    player = WasapiPlayback(opener=_opener(stream))
    player.load(TrackSource(path=one), OutputRequest(sample_rate=RATE, bit_depth=DEPTH))
    player.queue_next(TrackSource(path=two))
    player.play()
    _play_out(player)

    assert stream.starts == 1, "the stream was started more than once"
    assert stream.stops == 0, "the stream was stopped at the seam"
    assert stream.closed is False, "the device was given back mid album"
    assert player.crossings == 1
    player.stop()


def test_a_follower_the_open_stream_cannot_carry_is_refused(
    tmp_path, stream: RecordingStream
) -> None:
    """A different rate needs a different device, which is a gap either way.

    Refused rather than joined badly: writing the wrong rate into an open
    stream would play it at the wrong speed, which is worse than the gap.
    """
    one = _written(tmp_path, "one.wav", _ramp(FIRST_FRAMES, 0.0))
    two = _written(tmp_path, "two.wav", _ramp(SECOND_FRAMES, 0.5), rate=48000)

    player = WasapiPlayback(opener=_opener(stream))
    player.load(TrackSource(path=one), OutputRequest(sample_rate=RATE, bit_depth=DEPTH))

    assert player.queue_next(TrackSource(path=two)) is False
    player.play()
    _play_out(player)
    assert player.crossings == 0, "it joined a stream it does not fit"
    player.stop()


def test_a_source_that_cannot_be_opened_is_refused_rather_than_raised(
    tmp_path, stream: RecordingStream
) -> None:
    """A missing follower must not take down the track that is playing."""
    one = _written(tmp_path, "one.wav", _ramp(FIRST_FRAMES, 0.0))
    player = WasapiPlayback(opener=_opener(stream))
    player.load(TrackSource(path=one), OutputRequest(sample_rate=RATE, bit_depth=DEPTH))

    assert player.queue_next(TrackSource(path=str(tmp_path / "gone.wav"))) is False
    player.stop()


def test_nothing_is_lined_up_against_a_device_with_nothing_loaded(
    stream: RecordingStream,
) -> None:
    """Every port method is safe to call in any state, this one included."""
    player = WasapiPlayback(opener=_opener(stream))
    assert player.queue_next(None) is False
    assert player.crossings == 0


def test_a_lined_up_source_can_be_taken_back(tmp_path, stream: RecordingStream) -> None:
    """Clearing has to close the file it opened, not just forget about it."""
    one = _written(tmp_path, "one.wav", _ramp(FIRST_FRAMES, 0.0))
    two = _written(tmp_path, "two.wav", _ramp(SECOND_FRAMES, 0.5))

    player = WasapiPlayback(opener=_opener(stream))
    player.load(TrackSource(path=one), OutputRequest(sample_rate=RATE, bit_depth=DEPTH))
    assert player.queue_next(TrackSource(path=two)) is True
    assert player.queue_next(None) is False
    player.play()
    _play_out(player)

    assert player.crossings == 0, "it ran into a follower that was taken back"
    assert stream.written.shape[0] == FIRST_FRAMES
    player.stop()
