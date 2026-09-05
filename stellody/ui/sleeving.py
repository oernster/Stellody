"""What a press on a sleeve means.

The rule is small and the reasoning behind it is not, which is why it is here
rather than inside the module that shows the library: reading it takes longer
than reading everything around it.
"""

from __future__ import annotations

from PySide6.QtCore import QEvent, QObject, Qt
from PySide6.QtWidgets import QListView


class SleeveToggle(QObject):
    """Turns a second press on the open sleeve into a request to shut it.

    Read at the PRESS rather than at the click, because Qt moves the current
    index during the press: by the time `clicked` arrives, a first press on a
    fresh sleeve and a second press on the open one look alike. Pressing at all
    is also what makes a sleeve whose pane was closed open again, since it is
    still the current one and a selection that does not change says nothing.
    """

    def __init__(self, grid: QListView, viewing) -> None:
        super().__init__(grid)
        self._grid = grid
        self._viewing = viewing
        grid.viewport().installEventFilter(self)

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        """Shut the pane on a second LEFT press; the pane is the left button's.

        The left button opens the pane and shuts it. Every other button is
        taken and dropped, so the pane neither opens nor shuts under a right
        press: reaching for a sleeve's menu is not asking to see the album;
        on the open sleeve it used to roll the pane up as the menu came out
        from under it.

        The menu itself is untouched. It arrives as a context-menu event of
        its own and reads the row under the CURSOR, never the current one, so
        taking the press away from the selection costs it nothing.
        """
        if event.type() is not QEvent.Type.MouseButtonPress:
            return False
        if event.button() is not Qt.MouseButton.LeftButton:
            # Eaten, so Qt never moves the current sleeve for it. A right
            # press is somebody asking for the menu; the menu reads the row
            # under the cursor rather than the current one, so nothing it
            # offers depends on the selection following the pointer. Left
            # alone, the selection moved and the pane opened an album nobody
            # asked to see.
            return True
        where = self._grid.indexAt(event.position().toPoint())
        if not where.isValid():
            return False
        if where == self._viewing.shown_index:
            self._viewing.close_album()
            # Eaten, so the sleeve stays the current one with its pane shut.
            # Qt would otherwise leave the selection exactly as it was anyway;
            # saying so here is what stops the press reopening what it closed.
            return True
        self._viewing.open_album_at(where)
        return False
