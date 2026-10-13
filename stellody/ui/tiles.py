"""One album drawn as a tile: its sleeve, its title and who it is by.

A grid of sleeves is not a list with pictures in it. Every tile is the same
size whatever the length of the names on it, the sleeve is centred rather than
flush against an edge, then a title too long for its tile is cut with an
ellipsis rather than allowed to run into its neighbour. Resting the pointer on
a line that was cut shows the whole of it. None of that is what an item view
does on its own, so it is drawn here.

The album a listener has opened underneath the grid wears the accent ring the
rest of the application uses to say where attention is, rather than a pointer
drawn at it. One vocabulary for one meaning.
"""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import QEvent, QModelIndex, QRect, QSize, Qt
from PySide6.QtGui import QColor, QFontMetrics, QHelpEvent, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView,
    QStyle,
    QStyledItemDelegate,
    QStyleOptionViewItem,
    QToolTip,
)

from stellody.ui.covering import DEFAULT_COVER_SIZE, CoverSize
from stellody.ui.row_text import Column
from stellody.ui.theme import RADIUS_PX, Mode, palette_for

TILE_PAD_PX = 10
TITLE_GAP_PX = 8
LINE_GAP_PX = 2
NAME_LINE_PX = 18
ARTIST_LINE_PX = 16
OPEN_RING_PX = 2
NO_ROW = -1

NAMES_HEIGHT_PX = TITLE_GAP_PX + NAME_LINE_PX + LINE_GAP_PX + ARTIST_LINE_PX


@dataclass(frozen=True, slots=True)
class NameLine:
    """One line of names under a sleeve: where it sits, all of it, what fits."""

    rect: QRect
    text: str
    shown: str

    @property
    def cut(self) -> bool:
        """Whether the tile could not hold all of it."""
        return self.shown != self.text


def tile_size(cover_px: int) -> QSize:
    """A tile holding a sleeve that size with its two lines under it.

    Derived rather than stated per size, so three grid sizes cannot drift into
    three different amounts of room for the same two lines of text. The names
    do not grow with the sleeve: a title is the same title at any size.
    """
    return QSize(
        cover_px + 2 * TILE_PAD_PX,
        cover_px + 2 * TILE_PAD_PX + NAMES_HEIGHT_PX,
    )


class AlbumTile(QStyledItemDelegate):
    """An album as a sleeve with its names under it."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._mode = Mode.DARK
        self._open_row = NO_ROW
        self._cover_px = int(DEFAULT_COVER_SIZE)

    def show_appearance(self, mode: Mode) -> None:
        """Follow the appearance the rest of the window is wearing."""
        self._mode = mode

    def show_cover_size(self, size: CoverSize) -> None:
        """Draw the sleeves at this size, with the tiles to match."""
        self._cover_px = int(size)

    @property
    def cover_px(self) -> int:
        """The size a sleeve is drawn at here."""
        return self._cover_px

    def show_open(self, row: int) -> None:
        """Ring the album whose pane is open; NO_ROW when none is."""
        self._open_row = row

    def sizeHint(self, option: QStyleOptionViewItem, index: QModelIndex) -> QSize:
        """Every tile the same size, whatever the names on it are."""
        return tile_size(self._cover_px)

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
            self._cover_px,
            self._cover_px,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        left = rect.left() + (rect.width() - drawn.width()) // 2
        top = rect.top() + TILE_PAD_PX + (self._cover_px - drawn.height()) // 2
        painter.drawPixmap(left, top, drawn)

    def helpEvent(
        self,
        event: QHelpEvent,
        view: QAbstractItemView,
        option: QStyleOptionViewItem,
        index: QModelIndex,
    ) -> bool:
        """The whole of a title or an artist the tile had to cut short.

        Only for a line that was cut: a tooltip repeating what is already in
        full on the tile says nothing. Asked of the same lines the tile drew,
        so the two cannot disagree about which was cut.
        """
        if event.type() == QEvent.Type.ToolTip and index.isValid():
            for line in self._lines(option.rect, index, option.fontMetrics):
                if line.cut and line.rect.contains(event.pos()):
                    QToolTip.showText(event.globalPos(), line.text, view)
                    return True
        return super().helpEvent(event, view, option, index)

    def _draw_names(
        self, painter: QPainter, rect: QRect, index: QModelIndex, palette
    ) -> None:
        """The title, then the artist under it, each cut to fit its tile."""
        colours = (palette.text, palette.text_dim)
        for line, colour in zip(
            self._lines(rect, index, painter.fontMetrics()), colours
        ):
            painter.setPen(QColor(colour))
            painter.drawText(
                line.rect,
                int(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter),
                line.shown,
            )

    def _lines(
        self, rect: QRect, index: QModelIndex, metrics: QFontMetrics
    ) -> tuple[NameLine, ...]:
        """Where the title and the artist sit in a tile, with what fits of each."""
        width = rect.width() - 2 * TILE_PAD_PX
        top = rect.top() + TILE_PAD_PX + self._cover_px + TITLE_GAP_PX
        lines = []
        for text, height in (
            (index.data(Qt.ItemDataRole.DisplayRole), NAME_LINE_PX),
            (
                index.sibling(index.row(), Column.ARTIST).data(
                    Qt.ItemDataRole.DisplayRole
                ),
                ARTIST_LINE_PX,
            ),
        ):
            whole = text or ""
            lines.append(
                NameLine(
                    rect=QRect(rect.left() + TILE_PAD_PX, top, width, height),
                    text=whole,
                    shown=metrics.elidedText(whole, Qt.TextElideMode.ElideRight, width),
                )
            )
            top += height + LINE_GAP_PX
        return tuple(lines)
