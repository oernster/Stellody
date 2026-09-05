"""Space chooses a row, exactly as Enter already does.

The model wants Enter and Space to be one key with two names at every stop.
Qt gives that nowhere and gives it away differently in each place: a menu item
ignores Space because the Windows styles answer `SH_Menu_SpaceActivatesItem`
with 0, while a list or a grid spends it on the selection instead of on the
row, measured. So Enter opened a track in the library and Space did nothing at
all in the same list.

The menu bar answers its own half of this, since a popup owns the keyboard
while it is up. This is the other half: the item views, which is the library
list, the album grid and the two track columns beside a sleeve.

As in the menu bar, Space is handed on AS an Enter rather than being given a
second implementation of choosing. A view already knows what activating a row
means and the window has already said what it wants done about it; a second
path to the same place is a second path to drift away from it.
"""

from __future__ import annotations

from PySide6.QtCore import QEvent, QObject, Qt
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import QAbstractItemView, QApplication

from stellody.ui.ring import holds_the_focus

CHOOSE_KEY = Qt.Key.Key_Space
# What Space is handed to the view as, so choosing has one implementation.
CHOSEN_AS = Qt.Key.Key_Return


class SpaceChooses(QObject):
    """Turns a Space press in an item view into the Enter it stands for."""

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        application = QApplication.instance()
        if application is not None:
            application.installEventFilter(self)

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        """Answer Space over a row; leave every other key where it was."""
        if event.type() is not QEvent.Type.KeyPress:
            return False
        if not isinstance(event, QKeyEvent) or event.key() != CHOOSE_KEY:
            return False
        if event.modifiers() is not Qt.KeyboardModifier.NoModifier:
            return False
        return self.choose(watched)

    def choose(self, view: QObject) -> bool:
        """Hand the view an Enter; False when there is no row to open.

        Asked of the object the key was DELIVERED to, which has to be the
        widget its window holds the focus on: a key nobody consumes is offered
        to the parent next, so anything less would answer for a container the
        keyboard was never on. `ring.holds_the_focus` says why.

        A view with nothing current has nothing to choose, so Space is left
        alone there rather than being swallowed to no effect.
        """
        if not isinstance(view, QAbstractItemView):
            return False
        if not holds_the_focus(view):
            return False
        if not view.currentIndex().isValid():
            return False
        for kind in (QEvent.Type.KeyPress, QEvent.Type.KeyRelease):
            QApplication.sendEvent(
                view, QKeyEvent(kind, CHOSEN_AS, Qt.KeyboardModifier.NoModifier)
            )
        return True
