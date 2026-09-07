"""Whether the writing on a progress bar can actually be read.

Written after it could not be. The bar drew its text in the muted colour over
the accent as a fill, which measured 1.29 to 1 in the light appearance and 1.32
to 1 in the dark one: writing at that ratio is a smudge rather than a sentence.
Nothing caught it because nothing measured it; the ratios quoted elsewhere in
the palette were recorded by hand and never asserted.

The instrument itself lives in `contrast_support.py`, since the results dialog
is measured the same way and one formula written twice is two formulas the day
either is touched.

A bar is the one surface in this application that carries one colour of text
across two backgrounds, so both are measured. The threshold is the ordinary one
for body text rather than the relaxed one for large text, since a percentage in
a toolbar is small.
"""

from __future__ import annotations

import pytest
from contrast_support import DISTINCT, READABLE, contrast

from stellody.ui.palette import Mode, palette_for


def test_the_measurement_agrees_with_the_standards_own_examples() -> None:
    """The instrument is checked before anything is measured with it."""
    assert contrast("#ffffff", "#000000") == pytest.approx(21, abs=0.01)
    assert contrast("#ffffff", "#ffffff") == pytest.approx(1, abs=0.01)


@pytest.mark.parametrize("mode", tuple(Mode))
def test_the_writing_on_a_bar_reads_over_the_part_that_is_filled(mode: Mode) -> None:
    """The half that was unreadable: 1.3 to 1 while a run was under way."""
    colour = palette_for(mode)
    assert contrast(colour.on_progress, colour.progress_fill) >= READABLE


@pytest.mark.parametrize("mode", tuple(Mode))
def test_the_writing_on_a_bar_reads_over_the_part_that_is_not(mode: Mode) -> None:
    """One colour of text has to carry across both halves, not just one."""
    colour = palette_for(mode)
    assert contrast(colour.on_progress, colour.progress_groove) >= READABLE


@pytest.mark.parametrize("mode", tuple(Mode))
def test_the_filled_part_can_be_told_from_the_groove_behind_it(mode: Mode) -> None:
    """A bar whose fill matched its groove would be readable and useless.

    Three to one rather than four and a half: this is a shape being told apart
    from another shape rather than writing being read.

    Either way of doing it counts, which is the change made on 2026-09-07 when
    the fill was darkened so the writing over it could be read. The groove in
    the dark appearance is nearly black, so a fill dark enough for white text
    cannot also stand off it by lightness; the boundary is then drawn as a line
    round the fill instead. What must not happen is NEITHER.
    """
    colour = palette_for(mode)
    by_fill = contrast(colour.progress_fill, colour.progress_groove)
    by_edge = min(
        contrast(colour.progress_edge, colour.progress_fill),
        contrast(colour.progress_edge, colour.progress_groove),
    )
    assert max(by_fill, by_edge) >= DISTINCT
