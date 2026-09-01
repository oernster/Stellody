"""What the visualiser shows: how loud each band is, right now.

The equalizer SHAPES what is heard; this measures it. The two share their bands
deliberately, so the bars that move are the band the slider lifts. A listener
who opens the equalizer while a record plays can then see which control owns
the sound in front of them, rather than working it out by moving sliders until
something changes. A second set of band edges would be a second vocabulary for
one idea.

**Two bars to each filter, not one.** Ten bars across a few centimetres read as
a level meter with gaps rather than as a spectrum, so each of the equalizer's
octave bands is split in half AT ITS OWN CENTRE. The pair then covers exactly
the octave that filter acts on, the split point is the frequency the slider is
named for, no band edge exists that the equalizer does not already have.
The relationship survives the doubling because it is derived from the filters
rather than chosen beside them: a slider owns a neighbouring pair, where
dividing again would need only a different count here.

Measuring is split from drawing the way designing a filter is split from
applying one. What a band's edges ARE, then what a magnitude MEANS once it has
been measured, is arithmetic over frequencies and can be checked with nothing
installed; the transform that produces those magnitudes reads blocks on their
way to the device and belongs beside them, in infrastructure.

**Decibels, not magnitudes.** Loudness is heard logarithmically, so a bar drawn
in proportion to magnitude spends its whole life near the floor with an
occasional spike. A range is chosen and everything below it reads as silence,
which is what a floor is for: the alternative is a display that never settles
because it is drawing the room tone of the recording.

**The bars fall on their own.** A block carries 92.9 milliseconds of audio, so
measurements arrive about eleven times a second; drawn only as they arrive the
display steps rather than moves. Between them each bar falls at a fixed rate,
so what is seen is a peak that was really measured and a descent that is
honest about being drawn. Falling is slower than rising: a bar rises to meet
whatever it is given, because a transient that is averaged away has been
missed rather than smoothed.
"""

from __future__ import annotations

import itertools
import math

from stellody.domain.equalising import BAND_COUNT, BAND_FREQUENCIES

# The quietest thing worth a pixel. Chosen as the range a listener can pick out
# on a small strip rather than the range the format can hold: a 96 dB scale
# spends most of its height on silences nobody can hear.
FLOOR_DB = -60.0
CEILING_DB = 0.0

# A bar is a fraction of the strip's height, so the whole scale is 0 to 1 and
# nothing here knows how many pixels tall anything is.
EMPTY = 0.0
FULL = 1.0

# How far a bar falls per second when nothing louder arrives. Slow enough to be
# followed by eye, fast enough that a bar is not still descending from the last
# chorus during the silence after it.
FALL_PER_SECOND = 2.2

# How many bars each of the equalizer's filters is drawn as. Two: enough that a
# few centimetres reads as a spectrum, few enough that every edge is still one
# the filters already have.
BARS_PER_FILTER = 2
BAR_COUNT = BAND_COUNT * BARS_PER_FILTER

# A filter is one octave wide, so its edges are its centre divided and
# multiplied by the same root.
_OCTAVE_EDGE = math.sqrt(2.0)

# math.log10 of nothing is undefined; a block of digital silence really is
# nothing rather than something very quiet.
_SILENT = 0.0
_DECIBELS_PER_DECADE = 20.0

SILENT_BANDS: tuple[float, ...] = (EMPTY,) * BAR_COUNT


def band_edges(sample_rate: int) -> tuple[tuple[float, float], ...]:
    """The low and high edge of every bar, in hertz, low to high.

    Each of the equalizer's filters becomes two bars, split at that filter's
    own centre, so the pair together covers exactly the octave it acts on and
    every edge is one the equalizer already has.

    The top edge is held below the Nyquist frequency: there is no content above
    it to measure; a bar reaching past it would report the noise at the very
    top of the transform as music.
    """
    limit = sample_rate / 2
    edges = []
    for centre in BAND_FREQUENCIES:
        octave = (centre / _OCTAVE_EDGE, centre, centre * _OCTAVE_EDGE)
        for low, high in itertools.pairwise(octave):
            bounded = min(low, limit)
            edges.append((bounded, max(bounded, min(high, limit))))
    return tuple(edges)


def as_decibels(magnitude: float, reference: float) -> float:
    """One band's magnitude on the decibel scale, floored rather than negative.

    The reference is what counts as full scale for the transform that produced
    the magnitude, so this stays ignorant of window functions and of how many
    points went into it: those belong with the transform.
    """
    if magnitude <= _SILENT or reference <= _SILENT:
        return FLOOR_DB
    return max(FLOOR_DB, _DECIBELS_PER_DECADE * math.log10(magnitude / reference))


def as_height(decibels: float) -> float:
    """Where on the strip a band at this level reaches, from 0 to 1."""
    if decibels <= FLOOR_DB:
        return EMPTY
    if decibels >= CEILING_DB:
        return FULL
    return (decibels - FLOOR_DB) / (CEILING_DB - FLOOR_DB)


def heights(magnitudes: tuple[float, ...], reference: float) -> tuple[float, ...]:
    """Every band's magnitude turned into the height it should be drawn at."""
    return tuple(as_height(as_decibels(one, reference)) for one in magnitudes)


def fallen(
    shown: tuple[float, ...],
    measured: tuple[float, ...],
    seconds: float,
) -> tuple[float, ...]:
    """Where the bars are after `seconds` with `measured` newly in hand.

    A bar rises to whatever it was given at once and falls towards it at a
    fixed rate. Rising instantly is the point: the transient is the thing worth
    seeing; a bar that eased up to it would arrive after it had gone.
    """
    drop = max(EMPTY, seconds) * FALL_PER_SECOND
    return tuple(
        max(was - drop, now) if now < was else now for was, now in zip(shown, measured)
    )
