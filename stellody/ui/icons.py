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

# The cross is drawn over the whole square rather than inset, because it reads
# as a strike across the icon rather than as a badge in a corner.
TRANSPARENT = Qt.GlobalColor.transparent
SMOOTH = Qt.TransformationMode.SmoothTransformation
KEEP_ASPECT = Qt.AspectRatioMode.KeepAspectRatio
CENTRED = Qt.AlignmentFlag.AlignCenter


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


def glyph_icon(glyph: str, size_px: int, colour: str) -> QIcon:
    """One character drawn as artwork, at the size a button will draw it.

    For a control whose picture is a shape every font already carries, where
    a file would be a second thing to ship and to keep in step with the
    others. Measured on 2026-09-08 against this machine's own font files:
    Segoe UI Symbol carries the two joined squares, so Qt's own fallback
    finds it where the interface font does not.

    Drawn in a colour handed in rather than in whatever the palette happens to
    be, since an icon is a picture and knows nothing about appearances.
    """
    size = QSize(size_px, size_px)
    canvas = QPixmap(size)
    canvas.fill(TRANSPARENT)
    painter = QPainter(canvas)
    painter.setPen(QColor(colour))
    face = painter.font()
    face.setPixelSize(size_px)
    painter.setFont(face)
    painter.drawText(QRect(0, 0, size_px, size_px), CENTRED, glyph)
    painter.end()
    return QIcon(canvas)


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
