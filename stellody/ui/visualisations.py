"""The ways the visualiser can draw the same twenty measurements.

Four of them, stepped through by one button on the bottom strip: the plain
bars it always had, then a meter, a wave and a flame. Every style draws the
SAME bands from the same measurement, so switching changes how the music looks
and never what is measured; nothing upstream is told which style is on show.

One button cycling rather than four buttons or a menu: the strip has room for
one more picture and none for a choice. A style is also something tried by
pressing until one is liked rather than picked by name. The button's artwork shows the
cycle; its tooltip names the style a press moves to, which is the rule every
other picture on the strip follows.

The choice is written down by NAME, as the sleeve size is, so reordering or
adding a style cannot turn somebody's choice into a different one.
"""

from __future__ import annotations

from enum import StrEnum


class Visualisation(StrEnum):
    """One way of drawing the bands, in the order a press steps through them."""

    BARS = "bars"
    METER = "meter"
    WAVE = "wave"
    FLAME = "flame"


VISUALISATIONS = tuple(Visualisation)
DEFAULT_VISUALISATION = Visualisation.BARS
# How each is named in a sentence, kept beside the styles so a new one cannot
# be added without words to offer it by.
SPOKEN = {
    Visualisation.BARS: "bars",
    Visualisation.METER: "the meter",
    Visualisation.WAVE: "the wave",
    Visualisation.FLAME: "the flame",
}


def next_visualisation(style: Visualisation) -> Visualisation:
    """The style a press would move to, wrapping round after the last."""
    return VISUALISATIONS[(VISUALISATIONS.index(style) + 1) % len(VISUALISATIONS)]


def stored_visualisation(stored: str) -> Visualisation:
    """The style a written-down choice names; the default when it names none.

    A value nobody recognises, from a later version or a hand-edited file,
    falls back to the plain bars rather than refusing to draw anything.
    """
    if stored in VISUALISATIONS:
        return Visualisation(stored)
    return DEFAULT_VISUALISATION


def visualisation_tooltip(following: Visualisation) -> str:
    """What the button says a press would do: switch to the style after this."""
    return f"Switch the visualiser to {SPOKEN[following]}"
