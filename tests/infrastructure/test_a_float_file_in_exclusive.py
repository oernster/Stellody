"""A floating point file reaches an integer stream as sound, never as bit perfect.

Found by the audit of 2026-10-03. A FLOAT WAV states 32 bits, so an exclusive
request for it found the device's 32 bit integer format and the reader asked
libsndfile for integers. libsndfile 1.2.2 does not scale a float file into
integers: a sine at half of full scale read back as nought, so the track played
as silence while the strip called it bit perfect.

A float file is now read as floats and converted here, scaled to the stream's
integer range and clipped to it. A conversion from float to integer is not bit
exact, so the report no longer claims it.
"""

from __future__ import annotations

import numpy as np
import pytest
import soundfile
from device_support import A_DEVICE, CheckingStream, play_out, stand_in_device

from stellody.domain.equalising import Equalisation
from stellody.domain.playback import (
    Loudness,
    OutputMode,
    OutputRequest,
    bit_perfect_as_played,
)
from stellody.domain.track import TrackSource
from stellody.infrastructure import wasapi
from stellody.infrastructure.audio import WasapiPlayback

RATE = 44100
FRAMES = 4410
HALF_SCALE = 0.5
# What a probe states for a FLOAT file; what it states for a DOUBLE one.
FLOAT_DEPTHS = {"FLOAT": 32, "DOUBLE": 64}
# Off the top and off the bottom of the scale, which a float file may hold.
BEYOND_FULL_SCALE = 1.5
# Within one step of the integer scale, for rounding.
ONE_STEP = 1


def _float_file(tmp_path, subtype: str, samples: np.ndarray) -> str:
    """A floating point WAV holding these samples."""
    path = tmp_path / f"{subtype}.wav"
    soundfile.write(str(path), samples, RATE, subtype=subtype)
    return str(path)


def _half_scale() -> np.ndarray:
    """Half of full scale on one channel, its negative on the other.

    A constant rather than a tone, so the level written can be read exactly:
    a sampled sine almost never lands on its own peak.
    """
    return np.array([[HALF_SCALE, -HALF_SCALE]] * FRAMES)


def _opener(request: OutputRequest, _device: object):
    """The real WASAPI module, standing in front of a stand-in device."""
    return wasapi.open_output(request, A_DEVICE)


def _played(tmp_path, monkeypatch, subtype: str, takes: tuple[str, ...], samples):
    """Play a float file exclusively; hand back the report and what was written."""
    streams: list[CheckingStream] = []
    stand_in_device(monkeypatch, streams, takes)
    player = WasapiPlayback(opener=_opener)
    request = OutputRequest(
        sample_rate=RATE, bit_depth=FLOAT_DEPTHS[subtype], mode=OutputMode.EXCLUSIVE
    )
    report = player.load(
        TrackSource(path=_float_file(tmp_path, subtype, samples)), request
    )
    player.play()
    play_out(player)
    player.stop()
    return report, streams[-1].written


@pytest.mark.parametrize("subtype", sorted(FLOAT_DEPTHS))
@pytest.mark.parametrize("dtype", wasapi.CANDIDATE_DTYPES)
def test_a_float_file_is_heard_at_its_own_level(
    tmp_path, monkeypatch, subtype: str, dtype: str
) -> None:
    """Half of full scale in the file is half of the integer scale written."""
    report, written = _played(tmp_path, monkeypatch, subtype, (dtype,), _half_scale())
    assert report.mode is OutputMode.EXCLUSIVE
    assert written.dtype == np.dtype(dtype)
    full = np.iinfo(dtype).max
    for level in (written[:, 0], -written[:, 1].astype(np.int64)):
        assert (
            abs(level.astype(np.int64) - round(HALF_SCALE * full)) <= ONE_STEP
        ).all()


@pytest.mark.parametrize("subtype", sorted(FLOAT_DEPTHS))
def test_a_float_file_on_an_integer_stream_is_not_bit_perfect(
    tmp_path, monkeypatch, subtype: str
) -> None:
    """The conversion is not exact, so the claim is not made."""
    report, _written = _played(
        tmp_path, monkeypatch, subtype, wasapi.CANDIDATE_DTYPES, _half_scale()
    )
    assert report.mode is OutputMode.EXCLUSIVE
    assert not report.is_bit_perfect
    assert not bit_perfect_as_played(report, Loudness(), Equalisation())


def test_a_float_file_beyond_full_scale_is_clipped_to_the_integer_range(
    tmp_path, monkeypatch
) -> None:
    """Samples past full scale stop at the ends of the range; none wrap round."""
    dtype = "int16"
    samples = np.array([[BEYOND_FULL_SCALE, -BEYOND_FULL_SCALE]] * FRAMES)
    _report, written = _played(tmp_path, monkeypatch, "FLOAT", (dtype,), samples)
    assert (written[:, 0] == np.iinfo(dtype).max).all()
    assert (written[:, 1] == np.iinfo(dtype).min).all()
