"""Making one icon out of two: a switch, plus the cross that says it is off.

The struck-through variants are composed here rather than drawn as their own
files, so the artwork has one source per switch. Redrawing the cross changes
every switch that uses it; a switch redrawn needs no second file kept in
step with it.

Composing at the size the button will draw at, rather than scaling a composite
afterwards, keeps the cross the same weight on every button whatever its
artwork measures.
"""

from __future__ import annotations

import pathlib

from PySide6.QtCore import QRect, QSize, Qt
from PySide6.QtGui import QColor, QIcon, QImage, QPainter, QPixmap

from stellody.ui.theme import HALF

# A count in the corner, the place one is looked for on a chat app's icon.
# Sized against the icon rather than in pixels, so it keeps its weight on a
# button of any size: tall enough for a figure read at a glance, short enough
# to leave the picture recognisable under it.
BADGE_SHARE = 0.45
# The figure against the height of the pill it sits in.
BADGE_FIGURE_SHARE = 0.7
# Beyond this the badge says "99+" and the tooltip carries the exact count:
# a fourth figure would cover the picture it belongs to.
BADGE_MOST = 99
BADGE_BEYOND = "{most}+"

# The cross is drawn over the whole square rather than inset, because it reads
# as a strike across the icon rather than as a badge in a corner.
TRANSPARENT = Qt.GlobalColor.transparent
SMOOTH = Qt.TransformationMode.SmoothTransformation
KEEP_ASPECT = Qt.AspectRatioMode.KeepAspectRatio


def _scaled(path: pathlib.Path, size: QSize) -> QPixmap | None:
    """The artwork at this size, kept square and centred; None when unreadable."""
    image = QImage(str(path))
    if image.isNull():
        return None
    return QPixmap.fromImage(image.scaled(size, KEEP_ASPECT, SMOOTH))


def _centred(inner: QPixmap, size: QSize) -> QRect:
    """Where a picture sits when it is centred in a square of this size."""
    return QRect(
        (size.width() - inner.width()) // 2,
        (size.height() - inner.height()) // 2,
        inner.width(),
        inner.height(),
    )


def plain_icon(path: pathlib.Path | None) -> QIcon:
    """One picture as an icon; an empty icon when the file is not there."""
    if path is None:
        return QIcon()
    return QIcon(str(path))


def struck_through(
    path: pathlib.Path | None, negative: pathlib.Path | None, size_px: int
) -> QIcon:
    """The picture with the cross laid over it, saying this switch is off.

    Either file missing leaves the other to speak for itself, because a switch
    that cannot be seen is worse than one whose state has to be read from its
    tooltip.
    """
    if path is None:
        return plain_icon(negative)
    size = QSize(size_px, size_px)
    base = _scaled(path, size)
    if base is None:
        return QIcon()
    canvas = QPixmap(size)
    canvas.fill(TRANSPARENT)
    painter = QPainter(canvas)
    painter.drawPixmap(_centred(base, size), base)
    cross = None if negative is None else _scaled(negative, size)
    if cross is not None:
        painter.drawPixmap(_centred(cross, size), cross)
    painter.end()
    return QIcon(canvas)


def badge_figure(count: int) -> str:
    """What the badge says for a count: the count, else the most it shows."""
    return str(count) if count <= BADGE_MOST else BADGE_BEYOND.format(most=BADGE_MOST)


def badged(
    path: pathlib.Path | None, count: int, fill: str, ink: str, size_px: int
) -> QIcon:
    """The picture with a count in a red pill at its top right corner.

    The picture missing still leaves the badge, which is the part saying
    there is anything here at all. The pill grows sideways with the figure
    and never past the picture's own width.
    """
    size = QSize(size_px, size_px)
    canvas = QPixmap(size)
    canvas.fill(TRANSPARENT)
    painter = QPainter(canvas)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    base = None if path is None else _scaled(path, size)
    if base is not None:
        painter.drawPixmap(_centred(base, size), base)
    height = round(size_px * BADGE_SHARE)
    font = painter.font()
    font.setBold(True)
    font.setPixelSize(round(height * BADGE_FIGURE_SHARE))
    painter.setFont(font)
    figure = badge_figure(count)
    # Half a pill's height of room round the figure, so a single digit sits
    # in a circle and longer ones in a pill with the same round ends.
    wanted = painter.fontMetrics().horizontalAdvance(figure) + height // HALF
    width = min(max(height, wanted), size_px)
    pill = QRect(size_px - width, 0, width, height)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor(fill))
    painter.drawRoundedRect(pill, height / HALF, height / HALF)
    painter.setPen(QColor(ink))
    painter.drawText(pill, Qt.AlignmentFlag.AlignCenter, figure)
    painter.end()
    return QIcon(canvas)
