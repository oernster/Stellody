"""The ways the visualiser can draw the same twenty measurements.

Ten of them, named, chosen from a list that lifts up over the button on the
bottom strip the way the output devices do. Every style draws the SAME bands
from the same measurement, so choosing changes how the music looks and never
what is measured; nothing upstream is told which style is on show.

A named list rather than a button stepping through them: stepped, ten styles
are nine presses from the last back to the first, with no way to tell which
comes next. Oliver asked for the list on 2026-10-12, once there were ten.

The choice is written down by NAME, as the sleeve size is, so reordering or
adding a style cannot turn somebody's choice into a different one.
"""

from __future__ import annotations

from enum import StrEnum


class Visualisation(StrEnum):
    """One way of drawing the bands, in the order the list offers them."""

    BARS = "bars"
    METER = "meter"
    WAVE = "wave"
    FLAME = "flame"
    MIRROR = "mirror"
    RAINBOW = "rainbow"
    SUNBURST = "sunburst"
    DOT_MATRIX = "dot matrix"
    SCOPE = "scope"
    BUBBLES = "bubbles"


VISUALISATIONS = tuple(Visualisation)
# What a new install draws in, ruled by Oliver on 2026-10-12. `fresh_start.py`.
DEFAULT_VISUALISATION = Visualisation.DOT_MATRIX
# What the list calls each, kept beside the styles so a new one cannot be
# added without a name to offer it by.
NAMES = {
    Visualisation.BARS: "Bars",
    Visualisation.METER: "Meter",
    Visualisation.WAVE: "Wave",
    Visualisation.FLAME: "Flame",
    Visualisation.MIRROR: "Mirror",
    Visualisation.RAINBOW: "Rainbow",
    Visualisation.SUNBURST: "Sunburst",
    Visualisation.DOT_MATRIX: "Dot matrix",
    Visualisation.SCOPE: "Scope",
    Visualisation.BUBBLES: "Bubbles",
}
VISUALISATION_TOOLTIP = "Choose how the visualiser draws"


def stored_visualisation(stored: str) -> Visualisation:
    """The style a written-down choice names; the default when it names none.

    A value nobody recognises, from a later version or a hand-edited file,
    falls back to the default rather than refusing to draw anything.
    """
    if stored in VISUALISATIONS:
        return Visualisation(stored)
    return DEFAULT_VISUALISATION
