"""How each visualisation is drawn, given where the bands and their peaks are.

Kept apart from the widget that runs the clock: what a frame LOOKS like is a
question of its own, with one answer per style, while when a frame is drawn is
the same for all of them. Each painter is handed the room inside the strip's
margin, the heights the bars have reached, the peaks they have left behind and
the palette, then draws; none keeps anything between frames.

Every style lays the bands across the room by the same arithmetic, so a band
sits in the same place whichever is on show and switching style moves nothing
sideways. Every style also keeps a mark on the floor in silence, for the reason
the bars always did: a strip with nothing in it must still read as a strip.

The colours are the palette's. The plain bars wear the accent, as they always
have; the other three wear the visualiser's own roles, taken from the artwork
of the button that switches between them.
"""

from __future__ import annotations

import itertools
from collections.abc import Callable

from PySide6.QtCore import QPointF, QRect, Qt
from PySide6.QtGui import (
    QBrush,
    QColor,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QPolygonF,
)

from stellody.ui.palette import Palette
from stellody.ui.theme import HALF
from stellody.ui.visualisations import Visualisation

# As tight as bars can be drawn and still be told apart. The whole thing is a
# few centimetres across and holds twenty bars, so every pixel spent on a gap
# is a pixel taken off a bar.
BAR_GAP_PX = 1
BAR_RADIUS_PX = 2
# What a band with nothing in it still shows: enough to say the band is there
# and too little to be mistaken for something being heard.
BASELINE_PX = 2
# The meter's lamps: each this tall, with this much dark between them, which
# at the strip's height gives eight or so to a column.
LAMP_PX = 2
LAMP_GAP_PX = 1
# The wave's lines. The curve is the heavier of the two because it is the
# music now; the peak line is a trace of where it has just been.
WAVE_LINE_PX = 1.5
PEAK_LINE_PX = 1.0
# How much of the strip shows through the wave's fill, so the line on top is
# what the eye follows rather than a solid block under it.
WAVE_FILL_OPACITY = 0.55
# Where the middle stop of a three colour ramp sits, from the floor up.
RAMP_MIDDLE = 0.5
# How deep the flame's valleys are against the lower of the two spikes they
# sit between: shallow enough that neighbouring bands read as one fire.
FLAME_VALLEY_SHARE = 0.35
FLAME_EDGE_PX = 1.0

Painter = Callable[
    [QPainter, QRect, tuple[float, ...], tuple[float, ...], Palette], None
]


def _span(inner: QRect, count: int) -> float:
    """How far apart neighbouring bands sit across the room."""
    return (inner.width() + BAR_GAP_PX) / count


def _tall(inner: QRect, height: float) -> float:
    """A height on the 0 to 1 scale in pixels, never below the baseline."""
    return max(BASELINE_PX, inner.height() * height)


def _ramp(inner: QRect, low: str, middle: str, high: str) -> QLinearGradient:
    """Three colours from the floor of the room to its ceiling."""
    ramp = QLinearGradient(
        QPointF(inner.left(), inner.bottom()), QPointF(inner.left(), inner.top())
    )
    ramp.setColorAt(0, QColor(low))
    ramp.setColorAt(RAMP_MIDDLE, QColor(middle))
    ramp.setColorAt(1, QColor(high))
    return ramp


def _band_points(inner: QRect, heights: tuple[float, ...]) -> list[QPointF]:
    """Each band's top at its own centre, with the two ends held at the edges."""
    span = _span(inner, len(heights))
    points = [
        QPointF(
            inner.left() + (band + 1 / HALF) * span, inner.bottom() - _tall(inner, h)
        )
        for band, h in enumerate(heights)
    ]
    return [
        QPointF(inner.left(), points[0].y()),
        *points,
        QPointF(inner.right(), points[-1].y()),
    ]


def _smooth(points: list[QPointF]) -> QPainterPath:
    """A curve through the midpoints, bending at each point rather than turning.

    Each band's top is a control point and the curve passes halfway between
    neighbours, which keeps it inside the room: a curve forced THROUGH every
    point overshoots above the tallest band and below the floor.
    """
    path = QPainterPath(points[0])
    for here, there in itertools.pairwise(points):
        path.quadTo(here, (here + there) / HALF)
    path.lineTo(points[-1])
    return path


def paint_bars(painter, inner, shown, peaks, palette) -> None:
    """The plain bars: one rounded column per band, in the accent."""
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor(palette.accent))
    span = _span(inner, len(shown))
    width = max(BASELINE_PX, int(span) - BAR_GAP_PX)
    for band, height in enumerate(shown):
        tall = int(_tall(inner, height))
        painter.drawRoundedRect(
            inner.left() + int(band * span),
            inner.bottom() - tall,
            width,
            tall,
            BAR_RADIUS_PX,
            BAR_RADIUS_PX,
        )


def paint_meter(painter, inner, shown, peaks, palette) -> None:
    """Columns of lamps, cool at the floor to hot at the top, with peak caps.

    One gradient over the whole room rather than a colour per lamp, so a lamp
    takes the colour of the height it sits at and a tall column runs through
    all three.
    """
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(
        QBrush(
            _ramp(inner, palette.visual_cool, palette.visual_warm, palette.visual_hot)
        )
    )
    pitch = LAMP_PX + LAMP_GAP_PX
    lamps = max(1, (inner.height() + LAMP_GAP_PX) // pitch)
    span = _span(inner, len(shown))
    width = max(BASELINE_PX, int(span) - BAR_GAP_PX)
    for band, (height, peak) in enumerate(zip(shown, peaks)):
        left = inner.left() + int(band * span)
        # The floor lamp is always lit: it is this style's baseline.
        for lamp in range(max(1, round(height * lamps))):
            painter.drawRect(
                left, inner.bottom() - LAMP_PX - lamp * pitch, width, LAMP_PX
            )
        cap = round(peak * lamps)
        if cap > 0:
            painter.fillRect(
                left,
                inner.bottom() - LAMP_PX - min(cap, lamps - 1) * pitch,
                width,
                LAMP_PX,
                QColor(palette.visual_hot),
            )


def paint_wave(painter, inner, shown, peaks, palette) -> None:
    """A smooth line over a filled sea, with the recent peaks traced above."""
    curve = _smooth(_band_points(inner, shown))
    sea = QPainterPath(curve)
    sea.lineTo(QPointF(inner.right(), inner.bottom()))
    sea.lineTo(QPointF(inner.left(), inner.bottom()))
    sea.closeSubpath()
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setOpacity(WAVE_FILL_OPACITY)
    painter.setBrush(
        QBrush(
            _ramp(inner, palette.visual_deep, palette.visual_deep, palette.visual_warm)
        )
    )
    painter.drawPath(sea)
    painter.setOpacity(1)
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.setPen(QPen(QColor(palette.visual_hot), PEAK_LINE_PX))
    painter.drawPath(_smooth(_band_points(inner, peaks)))
    painter.setPen(QPen(QColor(palette.visual_cool), WAVE_LINE_PX))
    painter.drawPath(curve)


def _flame(inner: QRect, heights: tuple[float, ...]) -> QPolygonF:
    """Spikes at each band's centre with shallow valleys between them."""
    span = _span(inner, len(heights))
    floor = inner.bottom()
    outline = [QPointF(inner.left(), floor)]
    previous = heights[0]
    for band, height in enumerate(heights):
        valley = min(previous, height) * FLAME_VALLEY_SHARE
        outline.append(
            QPointF(inner.left() + band * span, floor - _tall(inner, valley))
        )
        outline.append(
            QPointF(
                inner.left() + (band + 1 / HALF) * span, floor - _tall(inner, height)
            )
        )
        previous = height
    outline.append(QPointF(inner.right(), floor - BASELINE_PX))
    outline.append(QPointF(inner.right(), floor))
    return QPolygonF(outline)


def paint_flame(painter, inner, shown, peaks, palette) -> None:
    """A fire along the floor: red at its base, yellow only where it runs tall.

    The ramp spans the whole room rather than each spike, so a quiet band
    burns red and only a loud one reaches the yellow. A brighter core was
    tried and measured on a render: it filled the base, so the fire read as
    hottest at the bottom.
    """
    painter.setPen(QPen(QColor(palette.visual_blaze), FLAME_EDGE_PX))
    painter.setBrush(
        QBrush(
            _ramp(inner, palette.visual_ember, palette.visual_blaze, palette.visual_hot)
        )
    )
    painter.drawPolygon(_flame(inner, shown))


PAINTERS: dict[Visualisation, Painter] = {
    Visualisation.BARS: paint_bars,
    Visualisation.METER: paint_meter,
    Visualisation.WAVE: paint_wave,
    Visualisation.FLAME: paint_flame,
}
