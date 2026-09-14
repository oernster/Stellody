"""One column of an open album's tracks, asking for the height its rows take.

A list view asks for a default height whatever it holds, so the album pane was
the same size under an album of two tracks as under one of twenty: measured on
2026-09-14 at 300 pixels in all three cases, most of it empty under a short
album. This column states the height of the rows it shows instead, so the pane
can be as tall as its album and no taller. Where the page has less room than
that, the column is given less and scrolls, as it always did.
"""

from __future__ import annotations

from PySide6.QtCore import QModelIndex, QSize
from PySide6.QtWidgets import QHeaderView, QTreeView, QWidget

from stellody.ui.covering import RowCover
from stellody.ui.models import AlbumTreeModel
from stellody.ui.row_text import Column


class TrackColumn(QTreeView):
    """A column of tracks, as tall as the rows it has been left showing."""

    def sizeHint(self) -> QSize:
        """The rows laid end to end inside the frame; the width is Qt's."""
        hint = super().sizeHint()
        return QSize(hint.width(), self.rows_height() + 2 * self.frameWidth())

    def minimumSizeHint(self) -> QSize:
        """No taller than the rows themselves, when they are fewer than Qt's floor.

        A list view will not go below the room its scrollbar needs, measured at
        74 pixels offscreen, which is taller than a short album's rows: an album
        of two tracks and one of eight both opened the same pane. A column that
        holds all its rows needs no scrollbar, so that floor applies only to one
        that does not.
        """
        floor = super().minimumSizeHint()
        return QSize(floor.width(), min(floor.height(), self.sizeHint().height()))

    def rows_height(self) -> int:
        """How tall every row this column shows is, added together.

        Walked rather than counted and multiplied: a disc heading is a row too.
        The walk also passes over the rows hidden for belonging to the other
        column, so neither has to be accounted for separately.
        """
        total = 0
        index = self._first_shown()
        while index.isValid():
            total += self.rowHeight(index)
            index = self.indexBelow(index)
        return total

    def _first_shown(self) -> QModelIndex:
        """The first row of the album this column has not hidden; none else."""
        model = self.model()
        root = self.rootIndex()
        if model is None or not root.isValid():
            return QModelIndex()
        for row in range(model.rowCount(root)):
            if not self.isRowHidden(row, root):
                return model.index(row, Column.TITLE, root)
        return QModelIndex()


def track_column(parent: QWidget, model: AlbumTreeModel) -> TrackColumn:
    """One column of an album's tracks, on the library's own model."""
    view = TrackColumn(parent)
    view.setItemDelegate(RowCover(view))
    view.setModel(model)
    view.setUniformRowHeights(True)
    view.setAllColumnsShowFocus(True)
    view.setRootIsDecorated(False)
    view.setHeaderHidden(True)
    view.setSelectionBehavior(QTreeView.SelectionBehavior.SelectRows)
    view.setColumnHidden(Column.ARTIST, True)
    # The detail cell is shown here, unlike the artist's, because it is where
    # a track says what it has been played. It is empty until one has, so it
    # costs an album nobody has listened to nothing at all.
    header = view.header()
    header.setSectionResizeMode(Column.TITLE, QHeaderView.ResizeMode.Stretch)
    header.setSectionResizeMode(Column.DETAIL, QHeaderView.ResizeMode.ResizeToContents)
    header.setSectionResizeMode(Column.LENGTH, QHeaderView.ResizeMode.ResizeToContents)
    return view
