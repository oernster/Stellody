"""The grid of sleeves with the album pane under it, sharing one column of room.

The pane asks to be as tall as the album open in it and the grid takes what is
left. On its own that lets a long album push the grid down to less than a
sleeve, which leaves the album just picked with nowhere to be seen. So this page
keeps one whole row of sleeves for the grid; the pane may have the rest at most.

A row of sleeves rather than a count of tracks, because a row is what the grid
needs in order to show the album that was picked. The room that leaves the
pane then follows the window and the sleeve size instead of being a number
chosen here: a taller window lists more of a long album before it scrolls.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QListView, QVBoxLayout, QWidget

from stellody.ui.album_pane import AlbumPane


class CoversPage(QWidget):
    """The grid above, the album pane below it, which starts closed."""

    def __init__(self, parent: QWidget, grid: QListView, pane: AlbumPane) -> None:
        super().__init__(parent)
        # A holder, never a stop: the ring belongs to the views inside it.
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._grid = grid
        self._pane = pane
        column = QVBoxLayout(self)
        column.setContentsMargins(0, 0, 0, 0)
        column.setSpacing(0)
        column.addWidget(grid, 1)
        column.addWidget(pane)

    def fit_pane(self) -> None:
        """Let the pane have whatever leaves the grid one whole row of sleeves.

        Asked again whenever either side of that changes: the page's own height
        on a resize, the row's whenever the sleeves are drawn at another size.
        """
        grid = self._grid
        kept = grid.gridSize().height() + 2 * grid.frameWidth()
        self._pane.limit_height(max(0, self.height() - kept))

    def resizeEvent(self, event) -> None:
        """A different height is a different amount left over for the pane."""
        super().resizeEvent(event)
        self.fit_pane()
