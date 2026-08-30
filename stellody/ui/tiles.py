"""One album drawn as a tile: its sleeve, its title and who it is by.

A grid of sleeves is not a list with pictures in it. Every tile is the same
size whatever the length of the names on it, the sleeve is centred rather than
flush against an edge, then a title too long for its tile is cut with an
ellipsis rather than allowed to run into its neighbour. None of that is what an
item view does on its own, so it is drawn here.

The album a listener has opened underneath the grid wears the accent ring the
rest of the application uses to say where attention is, rather than a pointer
drawn at it. One vocabulary for one meaning.
"""

from __future__ import annotations

from PySide6.QtCore import QModelIndex, QRect, QSize, Qt
from PySide6.QtGui import QColor, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QStyle, QStyledItemDelegate, QStyleOptionViewItem

from stellody.ui.covering import GRID_COVER_PX
from stellody.ui.models import Column
from stellody.ui.theme import RADIUS_PX, Mode, palette_for

TILE_PAD_PX = 10
TITLE_GAP_PX = 8
LINE_GAP_PX = 2
NAME_LINE_PX = 18
ARTIST_LINE_PX = 16
OPEN_RING_PX = 2
NO_ROW = -1

TILE_WIDTH_PX = GRID_COVER_PX + 2 * TILE_PAD_PX
TILE_HEIGHT_PX = (
    GRID_COVER_PX
    + 2 * TILE_PAD_PX
    + TITLE_GAP_PX
    + NAME_LINE_PX
    + LINE_GAP_PX
    + ARTIST_LINE_PX
)


class AlbumTile(QStyledItemDelegate):
    """An album as a sleeve with its names under it."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._mode = Mode.DARK
        self._open_row = NO_ROW

    def show_appearance(self, mode: Mode) -> None:
        """Follow the appearance the rest of the window is wearing."""
        self._mode = mode

    def show_open(self, row: int) -> None:
        """Ring the album whose pane is open; NO_ROW when none is."""
        self._open_row = row

    def sizeHint(self, option: QStyleOptionViewItem, index: QModelIndex) -> QSize:
        """Every tile the same size, whatever the names on it are."""
        return QSize(TILE_WIDTH_PX, TILE_HEIGHT_PX)

    def paint(
        self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex
    ) -> None:
        """The sleeve, the title, then who it is by."""
        palette = palette_for(self._mode)
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        body = option.rect.adjusted(1, 1, -1, -1)
        if option.state & QStyle.StateFlag.State_Selected:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(palette.selection))
            painter.drawRoundedRect(body, RADIUS_PX, RADIUS_PX)
        self._draw_cover(painter, option.rect, index)
        self._draw_names(painter, option.rect, index, palette)
        if index.row() == self._open_row:
            pen = QPen(QColor(palette.accent))
            pen.setWidth(OPEN_RING_PX)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(body, RADIUS_PX, RADIUS_PX)
        painter.restore()

    def _draw_cover(self, painter: QPainter, rect: QRect, index: QModelIndex) -> None:
        """The sleeve, centred in the top of the tile."""
        cover = index.data(Qt.ItemDataRole.DecorationRole)
        if not isinstance(cover, QPixmap) or cover.isNull():
            return
        drawn = cover.scaled(
            GRID_COVER_PX,
            GRID_COVER_PX,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        left = rect.left() + (rect.width() - drawn.width()) // 2
        top = rect.top() + TILE_PAD_PX + (GRID_COVER_PX - drawn.height()) // 2
        painter.drawPixmap(left, top, drawn)

    def _draw_names(
        self, painter: QPainter, rect: QRect, index: QModelIndex, palette
    ) -> None:
        """The title, then the artist under it, each cut to fit its tile."""
        width = rect.width() - 2 * TILE_PAD_PX
        top = rect.top() + TILE_PAD_PX + GRID_COVER_PX + TITLE_GAP_PX
        for text, colour, height in (
            (index.data(Qt.ItemDataRole.DisplayRole), palette.text, NAME_LINE_PX),
            (
                index.sibling(index.row(), Column.ARTIST).data(
                    Qt.ItemDataRole.DisplayRole
                ),
                palette.text_dim,
                ARTIST_LINE_PX,
            ),
        ):
            line = QRect(rect.left() + TILE_PAD_PX, top, width, height)
            painter.setPen(QColor(colour))
            painter.drawText(
                line,
                int(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter),
                painter.fontMetrics().elidedText(
                    text or "", Qt.TextElideMode.ElideRight, width
                ),
            )
            top += height + LINE_GAP_PX
