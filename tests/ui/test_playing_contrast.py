"""Whether the mark on the playing row can be read through and told apart.

The mark fills the whole row behind writing it leaves untouched, so the
appearance's own text has to read on it. It also lands on the row that is
usually selected, sometimes flashed and ringed when focused, so it has to be
told apart from all three by hue: in lightness it sits within 1.07 to 1 of the
selection, which is what lets the text read on both.
"""

from __future__ import annotations

import pytest
from contrast_support import OPPOSITE_DEGREES, READABLE, contrast, hues_apart

from stellody.ui.palette import Mode, palette_for

# The colours the mark must not be mistaken for, each on the same row.
NEIGHBOURS = ("selection", "found", "ring")
# A third of a half turn: sixty degrees, where two hues stop reading as shades
# of one family. Measured for the pink in use, the nearest neighbour is `found`
# at 84 degrees in the light appearance and 82 in the dark one.
APART_ENOUGH_DEGREES = OPPOSITE_DEGREES / 3


@pytest.mark.parametrize("mode", tuple(Mode))
def test_the_writing_reads_on_the_mark(mode: Mode) -> None:
    """The row keeps its own text colour, so that is what is measured."""
    colour = palette_for(mode)
    assert contrast(colour.text, colour.playing) >= READABLE


@pytest.mark.parametrize("mode", tuple(Mode))
@pytest.mark.parametrize("neighbour", NEIGHBOURS)
def test_the_mark_is_told_apart_from_what_shares_its_row(
    mode: Mode, neighbour: str
) -> None:
    """By hue, since lightness is already spent on the writing."""
    colour = palette_for(mode)
    apart = hues_apart(colour.playing, getattr(colour, neighbour))
    assert apart >= APART_ENOUGH_DEGREES
