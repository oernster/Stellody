"""The six later visualisations: mirror, rainbow, sunburst, dot matrix, scope, bubbles.

Kept apart from `spectrum_painting.py`, which holds the first four and the
arithmetic every style shares; one file holding all ten would pass the line
cap. Each painter here follows the same contract as those: handed the room
inside the strip's margin, the heights, the peaks and the palette, it draws
and keeps nothing between frames.

Each is a different SHAPE as well as a different colour, so no two read as the
same display retinted: bars reflected about a middle line, bars each in a hue
of their own, rays from a hub, round lamps, a single trace, swelling circles.
Every one still marks the floor in silence, for the reason the bars always did.
"""

from __future__ import annotations

import math

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QLinearGradient, QPen, QRadialGradient

from stellody.ui.palette import Palette
from stellody.ui.spectrum_painting import (
    BAR_GAP_PX,
    BAR_RADIUS_PX,
    BASELINE_PX,
    RAMP_MIDDLE,
    band_span,
    drawn_height,
)
from stellody.ui.theme import HALF

# How strongly a lamp that is not lit still shows its colour, so the matrix
# reads as a matrix in silence rather than as nothing.
UNLIT_OPACITY = 0.18
DOT_GAP_PX = 2
# How much of the strip shows through a bubble, so overlapping bubbles mix.
BUBBLE_OPACITY = 0.55
BUBBLE_MIN_PX = 2.0
# The loudest bubble's radius against the distance between two bands.
BUBBLE_REACH = 1.2
# The scope's trace: a wide faint stroke under a fine bright one reads as glow.
SCOPE_GLOW_PX = 4.0
SCOPE_GLOW_OPACITY = 0.3
SCOPE_LINE_PX = 1.5
# The sunburst's hub, as a share of the longest ray.
HUB_SHARE = 0.18
# Rays fan across a half turn, left to right.
HALF_TURN = math.pi


def band_colour(palette: Palette, band: int, count: int) -> QColor:
    """The rainbow hue nearest this band's place from the lowest to the highest."""
    hues = palette.visual_rainbow
    if count <= 1:
        return QColor(hues[0])
    return QColor(hues[round(band / (count - 1) * (len(hues) - 1))])


def _column_width(span: float) -> int:
    return max(BASELINE_PX, int(span) - BAR_GAP_PX)


def paint_mirror(painter, inner, shown, peaks, palette) -> None:
    """Bars reflected about the middle line: magenta at the middle, cyan out."""
    middle = inner.top() + inner.height() / HALF
    fade = QLinearGradient(QPointF(0, inner.top()), QPointF(0, inner.bottom()))
    fade.setColorAt(0, QColor(palette.visual_cool))
    fade.setColorAt(RAMP_MIDDLE, QColor(palette.visual_warm))
    fade.setColorAt(1, QColor(palette.visual_cool))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QBrush(fade))
    span = band_span(inner, len(shown))
    width = _column_width(span)
    for band, height in enumerate(shown):
        reach = max(BASELINE_PX, inner.height() * height) / HALF
        painter.drawRoundedRect(
            QRectF(inner.left() + int(band * span), middle - reach, width, reach * 2),
            BAR_RADIUS_PX,
            BAR_RADIUS_PX,
        )


def paint_rainbow(painter, inner, shown, peaks, palette) -> None:
    """A bar to each band in a hue of its own, with its peak as a dot above."""
    painter.setPen(Qt.PenStyle.NoPen)
    span = band_span(inner, len(shown))
    width = _column_width(span)
    for band, (height, peak) in enumerate(zip(shown, peaks)):
        painter.setBrush(band_colour(palette, band, len(shown)))
        left = inner.left() + int(band * span)
        tall = drawn_height(inner, height)
        painter.drawRoundedRect(
            QRectF(left, inner.bottom() - tall, width, tall),
            BAR_RADIUS_PX,
            BAR_RADIUS_PX,
        )
        if peak > height:
            top = inner.bottom() - drawn_height(inner, peak)
            painter.drawEllipse(QRectF(left, top, width, width))


def paint_sunburst(painter, inner, shown, peaks, palette) -> None:
    """Rays fanning up from a hub at the foot, longer as each band is louder.

    The fan is half an ellipse as wide as the strip and as tall as it, rather
    than half a circle: a circle as tall as the strip used a third of its width,
    measured on a render on 2026-10-12.
    """
    hub = QPointF(inner.left() + inner.width() / HALF, inner.bottom())
    wide, high = inner.width() / HALF, float(inner.height())
    glow = QRadialGradient(hub, max(wide, high))
    glow.setColorAt(0, QColor(palette.visual_warm))
    glow.setColorAt(RAMP_MIDDLE, QColor(palette.visual_blaze))
    glow.setColorAt(1, QColor(palette.visual_hot))
    count = len(shown)
    pen = QPen(QBrush(glow), max(BASELINE_PX, HALF_TURN * high * HUB_SHARE / count))
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    painter.setPen(pen)
    for band, height in enumerate(shown):
        angle = HALF_TURN - (band + 1 / HALF) / count * HALF_TURN
        across, up = math.cos(angle), math.sin(angle)
        reach = HUB_SHARE + (1 - HUB_SHARE) * height
        painter.drawLine(
            QPointF(
                hub.x() + wide * HUB_SHARE * across, hub.y() - high * HUB_SHARE * up
            ),
            QPointF(hub.x() + wide * reach * across, hub.y() - high * reach * up),
        )
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor(palette.visual_hot))
    painter.drawEllipse(hub, wide * HUB_SHARE / HALF, high * HUB_SHARE / HALF)


def paint_dot_matrix(painter, inner, shown, peaks, palette) -> None:
    """Round lamps in columns, lit to each band's height in the band's hue."""
    painter.setPen(Qt.PenStyle.NoPen)
    span = band_span(inner, len(shown))
    across = _column_width(span)
    pitch = across + DOT_GAP_PX
    rows = max(1, (inner.height() + DOT_GAP_PX) // pitch)
    for band, height in enumerate(shown):
        painter.setBrush(band_colour(palette, band, len(shown)))
        left = inner.left() + int(band * span)
        lit = max(1, round(height * rows))
        for row in range(rows):
            painter.setOpacity(1 if row < lit else UNLIT_OPACITY)
            painter.drawEllipse(
                QRectF(left, inner.bottom() - across - row * pitch, across, across)
            )
    painter.setOpacity(1)


def paint_scope(painter, inner, shown, peaks, palette) -> None:
    """One green trace swinging about the middle, louder bands swinging wider."""
    middle = inner.top() + inner.height() / HALF
    span = band_span(inner, len(shown))
    points = [QPointF(inner.left(), middle)]
    for band, height in enumerate(shown):
        swing = max(BASELINE_PX, inner.height() * height) / HALF
        # Alternate sides, as a waveform crosses its middle.
        side = 1 if band % 2 else -1
        points.append(
            QPointF(inner.left() + (band + 1 / HALF) * span, middle + side * swing)
        )
    points.append(QPointF(inner.right(), middle))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.setPen(QPen(QColor(palette.border), 1, Qt.PenStyle.DotLine))
    painter.drawLine(QPointF(inner.left(), middle), QPointF(inner.right(), middle))
    scope = QColor(palette.visual_scope)
    painter.setOpacity(SCOPE_GLOW_OPACITY)
    painter.setPen(QPen(scope, SCOPE_GLOW_PX))
    painter.drawPolyline(points)
    painter.setOpacity(1)
    painter.setPen(QPen(scope, SCOPE_LINE_PX))
    painter.drawPolyline(points)


def paint_bubbles(painter, inner, shown, peaks, palette) -> None:
    """A bubble to each band, swelling and rising as the band is louder."""
    span = band_span(inner, len(shown))
    # A little wider than a band at its loudest, so neighbours touch and
    # overlap rather than swamp each other: half the strip's height swamped
    # the whole row, measured on a render on 2026-10-12.
    largest = min(inner.height() / HALF, span * BUBBLE_REACH)
    for band, height in enumerate(shown):
        colour = band_colour(palette, band, len(shown))
        radius = BUBBLE_MIN_PX + (largest - BUBBLE_MIN_PX) * height
        # Louder bubbles float higher, so the row uses the strip's height too.
        rise = (inner.height() - radius * 2) * height
        centre = QPointF(
            inner.left() + (band + 1 / HALF) * span, inner.bottom() - radius - rise
        )
        painter.setPen(QPen(colour, 1))
        painter.setBrush(colour)
        painter.setOpacity(BUBBLE_OPACITY)
        painter.drawEllipse(centre, radius, radius)
    painter.setOpacity(1)
