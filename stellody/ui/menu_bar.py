"""A menu bar whose titles are stops on the ring, one press each.

The keyboard model wants each menu title to be its own stop: Tab and the
horizontal arrows walk File, View, Sound and Help; a title is HIGHLIGHTED as
the ring passes over it; Down opens the one under the cursor.

**Qt cannot express that natively and the obvious route is a trap.** Measured
on Qt 6.11.2: `setActiveAction` does not highlight a title, it OPENS it, with
or without focus on the bar, as a real popup window. F10 does the same. Hiding
the popup afterwards clears the highlight, so highlighted and open are one
state rather than two. Qt reaches a menu bar with Alt or F10 alone and gives it
no tab focus at all, so left as it comes it is not on the ring in the first
place.

So the cursor is this widget's own, exactly as a tab strip's is: an index it
keeps, a ring it paints on the title's own rectangle, plus a bounded walk
reporting when it has run out so the outer ring can carry on. Nothing here fights
Qt; the popup is still Qt's, opened by asking for the active action once the
listener presses Down.

The ring colour arrives through the stylesheet as a property rather than being
reached for, so the palette stays the one home for it, as `ringed_check.py`
does for the same reason.
"""

from __future__ import annotations

from PySide6.QtCore import Property, Qt
from PySide6.QtGui import QColor, QFocusEvent, QKeyEvent, QPainter, QPen
from PySide6.QtWidgets import QMenuBar, QWidget

RING_PX = 2
RING_RADIUS_PX = 4
RING_INSET_PX = 1
# What the stylesheet names to reach this bar and no other. A bare QMenuBar
# rule would hand the colour to every menu bar in the process, including the
# plain one any other window makes, which Qt then complains about by name.
OBJECT_NAME = "RingedMenuBar"
# Nowhere. A bar the ring has not reached shows no cursor at all, which is the
# first of the three ring states: no ring at rest.
NOWHERE = -1
FORWARD = 1
BACKWARD = -1
# Tab and the right arrow step the ring forward, Shift+Tab and the left arrow
# back, which is the contract at every stop rather than a menu speciality.
#
# Tab is named here and not left to `focusNextPrevChild` because a menu bar
# never asks that question: measured, Tab arrives at `keyPressEvent` and Qt's
# own handler moves the focus off the bar from there, so an override of the
# focus walk alone is never consulted and the titles are passed straight over.
FORWARD_KEYS = (Qt.Key.Key_Tab, Qt.Key.Key_Right)
BACKWARD_KEYS = (Qt.Key.Key_Backtab, Qt.Key.Key_Left)
# What opens the menu under the cursor. Down is the model's own; Enter and
# Space are the activate pair, which Qt gives a bar title neither of.
OPEN_KEYS = (
    Qt.Key.Key_Down,
    Qt.Key.Key_Return,
    Qt.Key.Key_Enter,
    Qt.Key.Key_Space,
)
BY_KEYBOARD = (
    Qt.FocusReason.TabFocusReason,
    Qt.FocusReason.BacktabFocusReason,
)


class RingedMenuBar(QMenuBar):
    """A menu bar that walks its own titles and paints where the ring is."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        # Qt gives a menu bar no focus at all otherwise, so it could never be
        # a stop however the window states its ring.
        self.setObjectName(OBJECT_NAME)
        self.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        self._cursor = NOWHERE
        self._ring = ""

    # The stylesheet hands the colour down, so the palette stays its one home.
    def _read_ring(self) -> str:
        return self._ring

    def _write_ring(self, colour: str) -> None:
        self._ring = colour
        self.update()

    ringColour = Property(str, _read_ring, _write_ring)

    @property
    def cursor_at(self) -> int:
        """Which title the ring is on; NOWHERE when it is not on the bar."""
        return self._cursor

    def _usable(self, index: int) -> bool:
        """Whether the title at an index is one the ring should offer."""
        actions = self.actions()
        if not 0 <= index < len(actions):
            return False
        action = actions[index]
        return action.isEnabled() and action.isVisible()

    def enter_cursor(self, delta: int) -> None:
        """Take the ring at the end it arrives from.

        Forward enters at the first title and backward at the last, so a pass
        in either direction reaches every one of them rather than only those
        on one side of wherever the cursor happened to be left.
        """
        self._cursor = NOWHERE if delta == FORWARD else len(self.actions())
        self.step_cursor(delta)

    def step_cursor(self, delta: int) -> bool:
        """Move to the next usable title; False once there are none left.

        Bounded rather than wrapping, which is the whole seam: the bar says
        whether it still has somewhere to go and the ring decides what to do
        when it does not. A wrapping walk here would trap the ring on the bar.
        """
        index = self._cursor + delta
        while 0 <= index < len(self.actions()):
            if self._usable(index):
                self._cursor = index
                self.update()
                return True
            index += delta
        return False

    def clear_cursor(self) -> None:
        """Put the ring out, for when the keyboard has moved on."""
        self._cursor = NOWHERE
        self.update()

    def open_current(self) -> bool:
        """Open the menu under the cursor; False when there is none to open.

        Asking for the active action is what opens it, measured: on Qt 6.11.2
        that call IS the opening rather than a highlight, which is why the
        cursor above is painted here instead of being asked of Qt.
        """
        if not self._usable(self._cursor):
            return False
        self.setActiveAction(self.actions()[self._cursor])
        return True

    def focusInEvent(self, event: QFocusEvent) -> None:
        """Take the cursor at whichever end the keyboard came from."""
        super().focusInEvent(event)
        if event.reason() in BY_KEYBOARD:
            forward = event.reason() is Qt.FocusReason.TabFocusReason
            self.enter_cursor(FORWARD if forward else BACKWARD)

    def focusOutEvent(self, event: QFocusEvent) -> None:
        """Put the cursor out, unless the bar's own popup took the focus."""
        super().focusOutEvent(event)
        if event.reason() is not Qt.FocusReason.PopupFocusReason:
            self.clear_cursor()

    def focusNextPrevChild(self, forward: bool) -> bool:
        """Walk the titles first; hand the ring on once they run out.

        The bounded walk answering False is the cue that the bar is finished;
        the base class then does what it always did. Note this is NOT where
        a Tab press arrives on a menu bar, measured: Qt never asks the question
        there, which is why the key handler below names Tab itself. This stays
        as the answer for anything that asks the focus walk directly.
        """
        if self.hasFocus() and self.step_cursor(FORWARD if forward else BACKWARD):
            return True
        return super().focusNextPrevChild(forward)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        """The arrows step the ring; Down, Enter and Space open a menu."""
        key = event.key()
        if key in FORWARD_KEYS or key in BACKWARD_KEYS:
            event.accept()
            self.focusNextPrevChild(key in FORWARD_KEYS)
            return
        if key in OPEN_KEYS and self.open_current():
            event.accept()
            return
        super().keyPressEvent(event)

    def paintEvent(self, event) -> None:
        """Qt's own bar, then the ring on the title the cursor is over."""
        super().paintEvent(event)
        if not self._ring or not self._usable(self._cursor):
            return
        where = self.actionGeometry(self.actions()[self._cursor])
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(QColor(self._ring), RING_PX))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(
            where.adjusted(
                RING_INSET_PX, RING_INSET_PX, -RING_INSET_PX, -RING_INSET_PX
            ),
            RING_RADIUS_PX,
            RING_RADIUS_PX,
        )
        painter.end()
