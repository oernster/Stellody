"""The grid of sleeves with the album pane under it, sharing one column of room.

The pane asks to be as tall as the album open in it and the grid takes what is
left. On its own that lets a long album push the grid down to less than a
sleeve, which leaves the album just picked with nowhere to be seen. So the page
states a ceiling and the pane never asks past it.

**The grid keeps half the page, whatever is open underneath it.** Reported by
Oliver on 2026-09-17 from a maximised window on a 4K 13 inch screen at 250%: a
thirteen track album left three rows of sleeves showing while a thirty three
track album on the same screen left one, so two albums looked like two rules.
Keeping one row was enough to see the sleeve that was picked and not enough to
go on browsing, which is what the grid is for. Half the page reads the same
under every album: a long one lists what it can and scrolls the rest.

The floor underneath that is still one whole row, for a window short enough
that half of it is less than a sleeve. Neither number is chosen here: both
follow the window and the size the sleeves are drawn at, so a taller window
lists more of a long album before it scrolls.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QListView, QVBoxLayout, QWidget

from stellody.ui.album_pane import AlbumPane

# What the grid keeps of the page, as a divisor: two is half of it. The pane
# has the rest, so every album stops in the same place however long it is.
GRID_SHARE_OF_PAGE = 2


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
        """Let the pane have whatever leaves the grid its share of the page.

        Half the page; one whole row of sleeves where that is the larger:
        the share is what keeps every album stopping in the same place, the row
        is what keeps the picked sleeve on screen in a short window.

        Asked again whenever any of that changes: the page's own height on a
        resize, the row's whenever the sleeves are drawn at another size.
        """
        grid = self._grid
        a_row = grid.gridSize().height() + 2 * grid.frameWidth()
        # Said as what the pane may have rather than as what the grid
        # keeps, so an odd pixel goes to the sleeves and the ceiling is
        # exactly the share whatever the page height is.
        kept = max(a_row, self.height() - self.height() // GRID_SHARE_OF_PAGE)
        self._pane.limit_height(max(0, self.height() - kept))

    def resizeEvent(self, event) -> None:
        """A different height is a different amount left over for the pane."""
        super().resizeEvent(event)
        self.fit_pane()
