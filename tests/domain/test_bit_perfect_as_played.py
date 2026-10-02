"""Bit perfect as played: the opened stream, the level and the curve together.

The report alone answers for the stream as opened. What reaches the device is
also shaped by the volume and the equalizer, which move while it plays, so the
claim is withdrawn whenever either would change a sample.
"""

from __future__ import annotations

from stellody.domain.equalising import BAND_COUNT, Equalisation
from stellody.domain.playback import (
    UNITY_VOLUME,
    Loudness,
    OutputMode,
    OutputReport,
    OutputRequest,
    bit_perfect_as_played,
)
from stellody.domain.track import CD_BIT_DEPTH, CD_SAMPLE_RATE

HALF_VOLUME = UNITY_VOLUME / 2
LIFT_DB = 3.0
FIRST_BAND = 0
TOP_BAND = BAND_COUNT - 1
# Half of it is under the top band's 16 kHz, so that band has nothing to act on.
LOW_RATE = 22050


def opened(
    mode: OutputMode = OutputMode.EXCLUSIVE, rate: int = CD_SAMPLE_RATE
) -> OutputReport:
    """A stream opened at the file's own rate and depth, in `mode`."""
    request = OutputRequest(sample_rate=rate, bit_depth=CD_BIT_DEPTH, mode=mode)
    return OutputReport(
        request=request, mode=mode, sample_rate=rate, bit_depth=CD_BIT_DEPTH
    )


def lifted(band: int) -> Equalisation:
    """A curve switched on that raises one band."""
    return Equalisation(enabled=True).with_band(band, LIFT_DB)


def test_an_untouched_exclusive_native_stream_is_bit_perfect() -> None:
    assert bit_perfect_as_played(opened(), Loudness(), Equalisation()) is True


def test_a_stream_the_report_refuses_stays_refused() -> None:
    """The level and the curve can only take the claim away, never grant it."""
    shared = opened(OutputMode.SHARED)
    assert bit_perfect_as_played(shared, Loudness(), Equalisation()) is False


def test_a_volume_below_unity_withdraws_it() -> None:
    quieter = Loudness(level=HALF_VOLUME)
    assert bit_perfect_as_played(opened(), quieter, Equalisation()) is False


def test_a_mute_withdraws_it_whatever_level_is_remembered() -> None:
    muted = Loudness(muted=True)
    assert bit_perfect_as_played(opened(), muted, Equalisation()) is False


def test_a_curve_that_shapes_the_sound_withdraws_it() -> None:
    assert bit_perfect_as_played(opened(), Loudness(), lifted(FIRST_BAND)) is False


def test_a_shaped_curve_switched_off_leaves_it_standing() -> None:
    off = lifted(FIRST_BAND).switched(False)
    assert bit_perfect_as_played(opened(), Loudness(), off) is True


def test_a_flat_curve_switched_on_leaves_it_standing() -> None:
    """No section is designed for it, so the engine touches nothing."""
    flat = Equalisation(enabled=True)
    assert bit_perfect_as_played(opened(), Loudness(), flat) is True


def test_a_band_above_half_the_rate_designs_nothing_so_leaves_it() -> None:
    """Judged by the sections the engine would run, not by the curve's look."""
    low = opened(rate=LOW_RATE)
    assert bit_perfect_as_played(low, Loudness(), lifted(TOP_BAND)) is True
