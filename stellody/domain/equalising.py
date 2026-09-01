"""Designing the filter the equalizer applies, apart from applying it.

Ten bands at the ISO octave centres, each a peaking filter that lifts or cuts
around its own frequency and leaves the rest of the spectrum alone. What a band
DOES is pure arithmetic over the sample rate, so it is worked out here and
handed to the engine as coefficients; the engine multiplies samples and knows
nothing about frequencies.

**A band left at nought is left OUT, not applied at unity.** A peaking filter
at nought decibels is exactly the identity, so dropping it is not an
approximation: it is the same answer for none of the cost. That is what lets a
flat equalizer cost nothing whatever in the signal path rather than merely
little, which is what the milestone asked for.

The arithmetic is the Audio EQ Cookbook's, hand rolled rather than taken from
scipy: it is a dozen lines that belong in the domain and can be tested without
an audio device, against tens of megabytes added to the packaged build.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

# The ISO octave centres. Ten of them, which is what a listener expects to see
# and what an octave-wide filter divides the audible range into.
BAND_FREQUENCIES = (31, 62, 125, 250, 500, 1000, 2000, 4000, 8000, 16000)
BAND_COUNT = len(BAND_FREQUENCIES)

# One octave wide, which is the spacing of the bands themselves, so neighbours
# meet rather than leaving a dip or piling up between them.
OCTAVE_Q = math.sqrt(2.0)

FLAT_DB = 0.0
MAXIMUM_GAIN_DB = 12.0
MINIMUM_GAIN_DB = -MAXIMUM_GAIN_DB

# A band at or above half the sample rate has no frequency to act on, so it is
# dropped rather than designed: the arithmetic divides by nothing there.
NYQUIST_DIVISOR = 2

_DECIBEL_ROOT = 40.0
_SEPARATOR = ","


@dataclass(frozen=True, slots=True)
class Biquad:
    """One second-order section, already normalised by its own `a0`.

    Normalising here rather than in the engine keeps the division in the layer
    that can be tested without a device; the hot loop is left with nothing
    but multiplications and additions.
    """

    b0: float
    b1: float
    b2: float
    a1: float
    a2: float


@dataclass(frozen=True, slots=True)
class Equalisation:
    """What each band is set to, plus whether the whole thing is switched on.

    The switch is kept apart from the gains so that turning the equalizer off
    does not throw away the curve somebody set up: it comes back as it was.
    """

    gains_db: tuple[float, ...] = (FLAT_DB,) * BAND_COUNT
    enabled: bool = False

    def __post_init__(self) -> None:
        if len(self.gains_db) != BAND_COUNT:
            raise ValueError(f"an equalisation needs {BAND_COUNT} bands")
        for gain in self.gains_db:
            if not MINIMUM_GAIN_DB <= gain <= MAXIMUM_GAIN_DB:
                raise ValueError(f"a band cannot be set to {gain} decibels")

    @property
    def flat(self) -> bool:
        """Whether it would change nothing, so nothing need be done at all."""
        return not self.enabled or all(gain == FLAT_DB for gain in self.gains_db)

    def with_band(self, band: int, gain_db: float) -> Equalisation:
        """The same settings with one band moved to a new gain."""
        moved = list(self.gains_db)
        moved[band] = gain_db
        return Equalisation(gains_db=tuple(moved), enabled=self.enabled)

    def switched(self, enabled: bool) -> Equalisation:
        """The same curve, switched on or off without being forgotten."""
        return Equalisation(gains_db=self.gains_db, enabled=enabled)

    def levelled(self) -> Equalisation:
        """The same switch with every band back at nought."""
        return Equalisation(enabled=self.enabled)


def peaking(
    frequency: int,
    gain_db: float,
    sample_rate: int,
    q: float = OCTAVE_Q,
) -> Biquad:
    """The peaking section for one band, from the Audio EQ Cookbook.

    A lift and a cut of the same size are reciprocals of each other, which is
    why the gain enters as a square root: `A` multiplies the numerator and
    divides the denominator, so undoing a boost is the same filter inverted
    rather than a differently shaped one.
    """
    amplitude = 10.0 ** (gain_db / _DECIBEL_ROOT)
    angle = 2.0 * math.pi * frequency / sample_rate
    alpha = math.sin(angle) / (2.0 * q)
    cosine = math.cos(angle)
    a0 = 1.0 + alpha / amplitude
    return Biquad(
        b0=(1.0 + alpha * amplitude) / a0,
        b1=(-2.0 * cosine) / a0,
        b2=(1.0 - alpha * amplitude) / a0,
        a1=(-2.0 * cosine) / a0,
        a2=(1.0 - alpha / amplitude) / a0,
    )


def cascade(equalisation: Equalisation, sample_rate: int) -> tuple[Biquad, ...]:
    """The sections worth running, which is only the bands that do something.

    A band at nought is dropped because it is the identity; a band at or
    above half the sample rate is dropped because there is nothing up there for
    it to act on. Both leave the answer exactly as it would have been.
    """
    if equalisation.flat:
        return ()
    highest = sample_rate / NYQUIST_DIVISOR
    return tuple(
        peaking(frequency, gain, sample_rate)
        for frequency, gain in zip(BAND_FREQUENCIES, equalisation.gains_db)
        if gain != FLAT_DB and frequency < highest
    )


def as_text(equalisation: Equalisation) -> str:
    """The whole setting as one string, for somewhere that stores strings."""
    return _SEPARATOR.join(str(gain) for gain in equalisation.gains_db)


def from_text(text: str, enabled: bool) -> Equalisation:
    """The setting that string held; a flat one when it holds anything else.

    Anything unreadable reads as flat rather than raising, since a stored
    setting that has been meddled with should cost a listener their curve
    rather than their player.
    """
    try:
        gains = tuple(float(part) for part in text.split(_SEPARATOR))
        return Equalisation(gains_db=gains, enabled=enabled)
    except ValueError:
        return Equalisation(enabled=enabled)
