"""The list of output devices, as a menu: one home for its words and its lines.

`OUTPUTS.md` FR-O02 to FR-O06, FR-O14 and FR-O17. The same list appears in two
places, popped up from the button on the bottom strip and as a submenu of the
Sound menu, so one function fills both from the transport's entries. Two
builders would be two lists that could come to disagree.

A menu rather than a list widget of its own, since a menu already is a vertical
list a keyboard walks with the arrows, chooses from with Enter and leaves with
Escape (FR-O18), with a mark for the line in force (FR-O06).
"""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QPoint
from PySide6.QtGui import QActionGroup
from PySide6.QtWidgets import QMenu, QWidget

from stellody.domain.outputs import OutputChoice, OutputEntry
from stellody.ui.dismissal import Dismissal

OUTPUT_TOOLTIP = "Choose the output device"
SYSTEM_DEFAULT_LABEL = "System default"
# A missing choice stays in the list, saying why it cannot be heard (FR-O14).
NOT_CONNECTED_LABEL = "{name} (not connected)"
# A single ampersand in a menu line marks the next letter as its shortcut and
# vanishes, so a device named "Rock & Roll" would read "Rock  Roll".
AMPERSAND = "&"
LITERAL_AMPERSAND = "&&"

Choose = Callable[[OutputChoice], None]


def entry_text(entry: OutputEntry) -> str:
    """The words one line of the list shows."""
    if entry.choice.follows_default:
        return SYSTEM_DEFAULT_LABEL
    if not entry.connected:
        return NOT_CONNECTED_LABEL.format(name=entry.label)
    return entry.label


def fill_output_menu(
    menu: QMenu, entries: tuple[OutputEntry, ...], choose: Choose
) -> None:
    """Replace the menu's lines with these, the chosen one marked.

    Safe while the menu is open, which is how a device connected with the
    list up appears in it at once (FR-O13). Safe from inside a line's own
    press as well, which is where choosing refills it: the old lines are taken
    off and let go of later rather than deleted at once, since `clear` would
    delete the very action still delivering the press.
    """
    for action in menu.actions():
        menu.removeAction(action)
        action.deleteLater()
    for old in menu.findChildren(QActionGroup):
        old.deleteLater()
    group = QActionGroup(menu)
    for entry in entries:
        action = menu.addAction(entry_text(entry).replace(AMPERSAND, LITERAL_AMPERSAND))
        action.setCheckable(True)
        action.setChecked(entry.chosen)
        group.addAction(action)
        action.triggered.connect(
            lambda _checked=False, entry=entry: choose(entry.choice)
        )
    menu.adjustSize()


class OutputMenu(QMenu):
    """The list, which remembers the press that closed it.

    A plain menu was enough until Oliver reported on 2026-09-20 that pressing
    the button again left the list up. Reproduced the same day: Qt closes a
    menu on a press outside it, so the menu was already down by the time the
    button's own click arrived and that click opened it afresh. It is the
    volume slider's defect on a second control, so it reads the same record
    (`dismissal.py`) rather than carrying a second copy of the knowledge.
    """

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self._dismissal = Dismissal()

    def mousePressEvent(self, event) -> None:
        """Close on a press outside, remembering where that press landed."""
        self._dismissal.note(self, event)
        super().mousePressEvent(event)

    def dismissed_by(self, button: QWidget) -> bool:
        """Whether the press that closed this landed on that button."""
        return self._dismissal.dismissed_by(button)


def pop_up_above(menu: OutputMenu, button: QWidget) -> None:
    """Show the menu over its button; take it down when it is already up.

    Above, since the button sits on the bottom strip; Qt keeps a menu on the
    screen, so one with no room above is moved down onto it. A second press
    closes it, as the help menu and the volume slider do: the press itself
    takes the menu down, so what reaches here is the click that follows and
    all it has to do is leave it down.
    """
    if menu.isVisible():
        menu.hide()
        return
    if menu.dismissed_by(button):
        return
    menu.popup(button.mapToGlobal(QPoint(0, -menu.sizeHint().height())))
