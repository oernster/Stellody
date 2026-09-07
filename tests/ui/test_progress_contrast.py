"""Whether the writing on a progress bar can actually be read.

Written after it could not be. The bar drew its text in the muted colour over
the accent as a fill, which measured 1.29 to 1 in the light appearance and 1.32
to 1 in the dark one: writing at that ratio is a smudge rather than a sentence.
Nothing caught it because nothing measured it; the ratios quoted elsewhere in
the palette were recorded by hand and never asserted.

A bar is the one surface in this application that carries one colour of text
across two backgrounds, so both are measured. The threshold is the ordinary one
for body text rather than the relaxed one for large text, since a percentage in
a toolbar is small.
"""

from __future__ import annotations

import pytest

from stellody.ui.palette import Mode, palette_for

# What ordinary text is asked to clear, from WCAG 2.1 contrast minimum.
READABLE = 4.5
# The sRGB luminance coefficients and the threshold below which a channel is
# linear rather than gamma encoded, both from that same definition.
RED_SHARE = 0.2126
GREEN_SHARE = 0.7152
BLUE_SHARE = 0.0722
LINEAR_BELOW = 0.03928
LINEAR_DIVISOR = 12.92
GAMMA_OFFSET = 0.055
GAMMA_EXPONENT = 2.4
FULL_CHANNEL = 255
# Keeps the ratio finite where one side is black.
FLARE = 0.05
CHANNELS = (0, 2, 4)
CHANNEL_DIGITS = 2


def _channel(value: int) -> float:
    """One channel, taken back to light from the encoding it is written in."""
    share = value / FULL_CHANNEL
    if share <= LINEAR_BELOW:
        return share / LINEAR_DIVISOR
    return ((share + GAMMA_OFFSET) / (1 + GAMMA_OFFSET)) ** GAMMA_EXPONENT


def luminance(colour: str) -> float:
    """How much light a colour carries, by the standard's own weighting."""
    digits = colour.lstrip("#")
    red, green, blue = (
        _channel(int(digits[at : at + CHANNEL_DIGITS], 16)) for at in CHANNELS
    )
    return RED_SHARE * red + GREEN_SHARE * green + BLUE_SHARE * blue


def contrast(one: str, other: str) -> float:
    """The ratio between two colours, brighter over darker."""
    first, second = luminance(one), luminance(other)
    brighter, darker = max(first, second), min(first, second)
    return (brighter + FLARE) / (darker + FLARE)


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
def test_the_fill_is_visible_against_the_groove_behind_it(mode: Mode) -> None:
    """A bar whose fill matched its groove would be readable and useless.

    Three to one rather than four and a half: this is a shape being told
    apart from another shape rather than writing being read.
    """
    colour = palette_for(mode)
    assert contrast(colour.progress_fill, colour.progress_groove) >= 3
