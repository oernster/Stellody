"""Which painter draws which visualisation: one table, one home.

The painters live in two modules (`spectrum_painting.py`, `spectrum_figures.py`)
because ten in one would pass the line cap; the table naming every one of them
sits here, above both, so neither has to know about the other's styles.
"""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QRect
from PySide6.QtGui import QPainter

from stellody.ui.palette import Palette
from stellody.ui.spectrum_figures import (
    paint_bubbles,
    paint_dot_matrix,
    paint_mirror,
    paint_rainbow,
    paint_scope,
    paint_sunburst,
)
from stellody.ui.spectrum_painting import (
    paint_bars,
    paint_flame,
    paint_meter,
    paint_wave,
)
from stellody.ui.visualisations import Visualisation

Painter = Callable[
    [QPainter, QRect, tuple[float, ...], tuple[float, ...], Palette], None
]

PAINTERS: dict[Visualisation, Painter] = {
    Visualisation.BARS: paint_bars,
    Visualisation.METER: paint_meter,
    Visualisation.WAVE: paint_wave,
    Visualisation.FLAME: paint_flame,
    Visualisation.MIRROR: paint_mirror,
    Visualisation.RAINBOW: paint_rainbow,
    Visualisation.SUNBURST: paint_sunburst,
    Visualisation.DOT_MATRIX: paint_dot_matrix,
    Visualisation.SCOPE: paint_scope,
    Visualisation.BUBBLES: paint_bubbles,
}
