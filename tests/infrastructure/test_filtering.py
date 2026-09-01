"""Running the cascade over blocks, measured rather than listened to.

A tone is put through at a band's own frequency and what comes out is measured
against what went in, which is the only way to say that the equalizer does what
it says. The same tone is then put through in one piece and in blocks; the
two must agree: a filter whose memory does not survive a block boundary sounds
like a tick at every boundary and looks perfectly correct in a single-block
test.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from stellody.domain.equalising import BAND_FREQUENCIES, Equalisation, cascade
from stellody.infrastructure.filtering import BiquadCascade

RATE = 44100
SECONDS = 1
BLOCK = 4096
LIFT_DB = 6.0
CENTRE = BAND_FREQUENCIES[5]
# The filter has to settle before its output means anything, so the first
# tenth of a second is measured over rather than against.
SETTLED = RATE // 10


def tone(frequency: int, frames: int, channels: int = 2) -> np.ndarray:
    """A steady sine, which is what a frequency response is measured with."""
    time = np.arange(frames, dtype="float64") / RATE
    wave = (0.25 * np.sin(2 * math.pi * frequency * time)).astype("float32")
    return np.repeat(wave.reshape(-1, 1), channels, axis=1)


def in_blocks(filtering: BiquadCascade, samples: np.ndarray) -> np.ndarray:
    """The same samples through the cascade a block at a time."""
    pieces = [
        filtering.process(samples[start : start + BLOCK].copy())
        for start in range(0, len(samples), BLOCK)
    ]
    return np.concatenate(pieces, axis=0)


def gain_db(before: np.ndarray, after: np.ndarray) -> float:
    """How much louder the tone came out, over the settled part of it."""
    was = np.sqrt(np.mean(before[SETTLED:, 0].astype("float64") ** 2))
    now = np.sqrt(np.mean(after[SETTLED:, 0].astype("float64") ** 2))
    return 20.0 * math.log10(now / was)


def lifted(band_frequency: int, gain: float = LIFT_DB) -> BiquadCascade:
    """A cascade holding one band, lifted."""
    band = BAND_FREQUENCIES.index(band_frequency)
    setting = Equalisation(enabled=True).with_band(band, gain)
    return BiquadCascade(cascade(setting, RATE))


def test_a_flat_cascade_hands_the_block_straight_back() -> None:
    """Not a copy and not a rounding: the very same object, untouched.

    This is what keeps an exclusive stream bit perfect while the equalizer is
    off; it also makes a flat equalizer cost nothing rather than little.
    """
    block = tone(CENTRE, BLOCK)
    filtering = BiquadCascade(cascade(Equalisation(), RATE))
    assert filtering.process(block) is block


def test_a_lifted_band_makes_its_own_frequency_louder_by_what_was_asked() -> None:
    """The measurement the milestone asks for: the bands change what is heard."""
    samples = tone(CENTRE, RATE * SECONDS)
    out = in_blocks(lifted(CENTRE), samples)
    assert gain_db(samples, out) == pytest.approx(LIFT_DB, abs=0.2)


def test_a_cut_band_makes_its_own_frequency_quieter() -> None:
    """A cut is not merely a lift with the sign of the label changed."""
    samples = tone(CENTRE, RATE * SECONDS)
    out = in_blocks(lifted(CENTRE, -LIFT_DB), samples)
    assert gain_db(samples, out) == pytest.approx(-LIFT_DB, abs=0.2)


def test_a_band_leaves_a_frequency_three_octaves_away_alone() -> None:
    """Otherwise one slider would be a volume control with extra steps."""
    distant = BAND_FREQUENCIES[2]
    samples = tone(distant, RATE * SECONDS)
    out = in_blocks(lifted(CENTRE), samples)
    assert abs(gain_db(samples, out)) < 1.0


def test_the_memory_survives_a_block_boundary() -> None:
    """A filter restarted at every block ticks at every block."""
    samples = tone(CENTRE, RATE // 2)
    whole = lifted(CENTRE).process(samples.copy())
    blocked = in_blocks(lifted(CENTRE), samples)
    assert np.allclose(whole, blocked, atol=1e-6), "the seams show"


def test_resetting_forgets_what_has_been_through() -> None:
    """A seek lands somewhere else entirely, so the old tail is not wanted."""
    samples = tone(CENTRE, BLOCK)
    filtering = lifted(CENTRE)
    first = filtering.process(samples.copy())
    filtering.reset()
    again = filtering.process(samples.copy())
    assert np.array_equal(first, again), "a reset cascade starts over exactly"


def test_a_boost_is_held_at_the_ceiling_rather_than_wrapping_round() -> None:
    """An integer that overflows turns a loud passage into noise."""
    loud = np.full((BLOCK, 2), 30000, dtype="int16")
    out = lifted(CENTRE, 12.0).process(loud)
    assert out.max() <= np.iinfo("int16").max
    assert out.min() >= -np.iinfo("int16").max


def test_a_float_boost_is_held_at_unity() -> None:
    """The same ceiling, said in the units a float stream uses."""
    loud = np.full((BLOCK, 2), 0.9, dtype="float32")
    out = lifted(CENTRE, 12.0).process(loud)
    assert out.max() <= 1.0


def test_a_block_that_changes_its_channel_count_is_given_new_memory() -> None:
    """One channel's memory carried into two would leak between them."""
    filtering = lifted(CENTRE)
    filtering.process(tone(CENTRE, BLOCK, channels=2))
    mono = filtering.process(tone(CENTRE, BLOCK, channels=1))
    assert mono.shape[1] == 1
