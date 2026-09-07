"""Whether every colour the results dialog writes in can be read.

FR-D34 asks for two artist colours that differ from each other, which is not
the same question as whether either can be read. The discovery bar was shipped
at 1.29 to 1 by satisfying one of those and not the other, so a pair chosen to
be distinguishable is exactly where it would happen again. NFR-USE-002.

Every colour the dialog uses is measured rather than the two new ones alone:
an album title and a line saying what went wrong are writing in the dialog too.
A requirement about "every colour the results dialog uses" is not met by
checking the ones somebody remembered.

Both surfaces are measured. A tree draws its rows on the surface colour and its
alternating rows on the other; which of those a given row lands on is not
something a colour gets to choose.
"""

from __future__ import annotations

import inspect
import pathlib
import re

import pytest
from contrast_support import OPPOSITE_DEGREES, READABLE, contrast, hues_apart

from stellody.ui.palette import Mode, Palette, palette_for
from stellody.ui.results_dialog import ResultsDialog

# What the dialog writes in: the two kinds of artist, an album title under
# either of them and the line that says what went wrong. Named by attribute so
# a colour added to the dialog without being measured is a name this list does
# not carry, rather than a ratio nobody took.
WRITING = ("source_artist", "candidate_artist", "text", "text_muted")
BEHIND = ("surface", "surface_alt")


def _surfaces(colour: Palette) -> tuple[str, ...]:
    """The backgrounds a row of this dialog can land on."""
    return tuple(getattr(colour, name) for name in BEHIND)


@pytest.mark.parametrize("mode", tuple(Mode))
@pytest.mark.parametrize("role", WRITING)
def test_every_colour_the_dialog_writes_in_can_be_read(mode: Mode, role: str) -> None:
    """The requirement in full: every colour, both surfaces, both appearances."""
    colour = palette_for(mode)
    for behind in _surfaces(colour):
        assert contrast(getattr(colour, role), behind) >= READABLE


# How far apart the two artist colours have to sit on the wheel. Measured for
# the pair in use: 187 degrees in the light appearance and 180 in the dark one,
# which is deep blue against amber. Two thirds of a half turn is the bar, so a
# later pair may be moved without being allowed to become two blues.
APART_ENOUGH_DEGREES = OPPOSITE_DEGREES * 2 / 3


@pytest.mark.parametrize("mode", tuple(Mode))
def test_the_two_kinds_of_artist_are_told_apart_from_each_other(mode: Mode) -> None:
    """Readable is not the same as distinguishable; FR-D34 wants both.

    Measured as a hue distance rather than as a lightness ratio, deliberately.
    Both colours have to be READ against one surface, so both sit at a similar
    distance from it: the pair in use measures 1.08 to 1 against each other in
    the light appearance while being unmistakable on screen. Asking for three
    to one between them would mean pushing one of the two towards the surface
    it is written on, which is the requirement above being broken to satisfy
    this one.
    """
    colour = palette_for(mode)
    assert (
        hues_apart(colour.source_artist, colour.candidate_artist)
        >= APART_ENOUGH_DEGREES
    )


def test_the_dialog_writes_in_nothing_that_was_not_measured() -> None:
    """The guard on the list above, so a fifth colour cannot slip in unmeasured.

    The module's own text is read rather than its behaviour, because a colour
    is chosen where it is named: a role used by a line nobody wrote a test for
    is still a role the dialog paints with.
    """
    source = pathlib.Path(inspect.getfile(ResultsDialog))
    used = set(re.findall(r"_colour\.([a-z_]+)", source.read_text(encoding="utf-8")))
    assert used <= set(WRITING)
