"""A file whose channel count is not the stream's still plays; else it says why.

Found by the audit of 2026-10-03: every stream is opened for two channels,
while a mono file reads back one. sounddevice refused the first write, the
error was not one the feeder caught, so the feeder died with the window still
saying the track was playing: silence, a frozen position and a queue that
never moved on.

A mono block is now written to every channel of the stream, which is what a
mono recording means. A file carrying channels the stream has no place for is
refused when it is opened, with the counts named. Anything else that goes
wrong on the feeder stops the track and is kept as the reason, rather than
leaving a dead thread behind a stream that claims to be playing.
"""

from __future__ import annotations

import numpy as np
import pytest
import soundfile
from device_support import (
    CheckingStream,
    FailingStream,
    mixer_opener,
    play_out,
    settle,
)

from stellody.domain.playback import OutputRequest, PlaybackError, PlaybackState
from stellody.domain.track import TrackSource
from stellody.infrastructure.audio import WasapiPlayback

RATE = 44100
DEPTH = 32
FRAMES = 10000
MONO = 1
SURROUND = 6


def _written(tmp_path, name: str, samples: np.ndarray) -> str:
    """One float WAV holding exactly these samples, so they read back exact."""
    path = tmp_path / name
    soundfile.write(str(path), samples, RATE, subtype="FLOAT")
    return str(path)


def _ramp(frames: int, channels: int) -> np.ndarray:
    """Distinct samples, so a dropped or doubled frame cannot hide in silence."""
    column = np.arange(frames, dtype="float32") / (2 * frames)
    return np.repeat(column.reshape(-1, 1), channels, axis=1)


def _request() -> OutputRequest:
    """What the transport asks for: the default two channels."""
    return OutputRequest(sample_rate=RATE, bit_depth=DEPTH)


def test_a_mono_file_is_written_to_every_channel_of_the_stream(tmp_path) -> None:
    """Each frame reaches both speakers sample for sample; the track ends."""
    samples = _ramp(FRAMES, MONO)
    streams: list[CheckingStream] = []
    player = WasapiPlayback(opener=mixer_opener(streams))
    player.load(TrackSource(path=_written(tmp_path, "mono.wav", samples)), _request())
    player.play()
    play_out(player)
    player.stop()

    written = streams[-1].written
    assert written.shape == (FRAMES, _request().channels)
    for channel in range(_request().channels):
        assert np.array_equal(written[:, channel], samples[:, 0])


def test_a_file_the_stream_has_no_place_for_is_refused_with_its_counts(
    tmp_path,
) -> None:
    """Six channels into two is refused on opening; the device is given back."""
    path = _written(tmp_path, "surround.wav", _ramp(FRAMES, SURROUND))
    streams: list[CheckingStream] = []
    player = WasapiPlayback(opener=mixer_opener(streams))
    with pytest.raises(PlaybackError, match=f"{SURROUND} channels"):
        player.load(TrackSource(path=path), _request())
    assert streams[-1].closed
    assert player.state is PlaybackState.STOPPED


def test_a_fault_on_the_feeder_stops_the_track_and_keeps_the_reason(
    tmp_path,
) -> None:
    """Not left playing behind a dead thread: held, with what went wrong."""
    path = _written(tmp_path, "stereo.wav", _ramp(FRAMES, _request().channels))
    streams: list[CheckingStream] = []
    player = WasapiPlayback(opener=mixer_opener(streams, FailingStream))
    player.load(TrackSource(path=path), _request())
    player.play()
    settle(player)

    assert player.state is not PlaybackState.PLAYING
    assert "a fault nobody planned for" in player.failure
    player.play()
    assert player.state is not PlaybackState.PLAYING, "a dead feeder cannot resume"
    player.stop()


def test_a_track_that_plays_has_no_failure(tmp_path) -> None:
    """The reason is empty unless something went wrong."""
    path = _written(tmp_path, "stereo.wav", _ramp(FRAMES, _request().channels))
    streams: list[CheckingStream] = []
    player = WasapiPlayback(opener=mixer_opener(streams))
    assert player.failure == ""
    player.load(TrackSource(path=path), _request())
    player.play()
    play_out(player)
    assert player.failure == ""
    player.stop()
