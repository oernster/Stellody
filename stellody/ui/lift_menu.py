"""A list lifted up over a button on the bottom strip, one line of it ticked.

Written for the output devices and shared since 2026-10-12 with the
visualiser's styles, which Oliver asked to be chosen "much like choose the
output device". One home for the behaviour, so the two lists open, close and
answer the keyboard the same way.

A menu rather than a list widget of its own, since a menu already is a vertical
list a keyboard walks with the arrows, chooses from with Enter and leaves with
Escape, with a mark for the line in force.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from PySide6.QtCore import QPoint
from PySide6.QtGui import QActionGroup
from PySide6.QtWidgets import QMenu, QWidget

from stellody.ui.dismissal import Dismissal

# A single ampersand in a menu line marks the next letter as its shortcut and
# vanishes, so a device named "Rock & Roll" would read "Rock  Roll".
AMPERSAND = "&"
LITERAL_AMPERSAND = "&&"


@dataclass(frozen=True, slots=True)
class Line:
    """One line of a lifted list: its words, whether it is ticked, its press."""

    text: str
    chosen: bool
    choose: Callable[[], None]


def emptied(menu: QMenu) -> None:
    """Take every line off the menu, safely even from inside a line's press.

    The lines, their groups and any submenu are let go of later rather than
    deleted at once, since `clear` would delete the very action still
    delivering the press that asked for the refill.
    """
    for action in menu.actions():
        menu.removeAction(action)
        action.deleteLater()
    for old in (*menu.findChildren(QActionGroup), *menu.findChildren(QMenu)):
        old.deleteLater()


def fill_choices(menu: QMenu, lines: tuple[Line, ...]) -> None:
    """Replace the menu's lines with these, the chosen one ticked.

    Safe while the menu is open, which is how a device connected with the
    list up appears in it at once. Safe from inside a line's own press as
    well, which is where choosing refills it: the old lines are taken off and
    let go of later rather than deleted at once, since `clear` would delete
    the very action still delivering the press.
    """
    emptied(menu)
    group = QActionGroup(menu)
    for line in lines:
        action = menu.addAction(line.text.replace(AMPERSAND, LITERAL_AMPERSAND))
        action.setCheckable(True)
        action.setChecked(line.chosen)
        group.addAction(action)
        action.triggered.connect(lambda _checked=False, line=line: line.choose())
    menu.adjustSize()


class LiftMenu(QMenu):
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


def pop_up_above(menu: LiftMenu, button: QWidget) -> None:
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
