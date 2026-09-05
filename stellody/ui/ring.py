"""Left and Right step the keyboard ring, at every stop that does not own them.

The ring itself is Qt's own focus chain, stated by the window with
`setTabOrder`, so Tab and Shift+Tab already walk it in reading order. The
horizontal arrows are meant to be those two keys by another name at every stop,
which Qt gives nowhere: a slider spends them changing its value, a grid spends
them moving its cursor sideways and a button ignores them. So they are answered
once, here, rather than in every control.

An application filter rather than a handler per widget, for the same reason the
menu bar keeps a cursor of its own: the stops are of a dozen different classes,
most of them Qt's own; subclassing each one to say the same sentence would put
the rule in a dozen places. This way a control added later is on the ring
the moment the window names it.

Three kinds of stop DO own the arrows and are left alone:

- Anything holding a caret. Left and Right move it, so a text field is left
  with them and is left with Tab as the way out, which is invariant 7 of the
  model.
- The library list, which is the one stated exception: Left and Right shut and
  open an album there, the only keyboard route into one. Said by
  the widget itself rather than named here, so the exception lives with the
  thing it exempts.
- The menu bar and its popups, which answer the horizontal keys themselves:
  the bar walks its titles and an open menu carries the drop along with it.
"""

from __future__ import annotations

from PySide6.QtCore import QEvent, QObject, Qt
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import (
    QAbstractSpinBox,
    QApplication,
    QLineEdit,
    QMenu,
    QMenuBar,
    QPlainTextEdit,
    QTextEdit,
    QWidget,
)

# The two keys this exists for. Tab and Shift+Tab are Qt's own and are not
# touched: intercepting a key that already works is how the two come to differ.
FORWARD_KEYS = (Qt.Key.Key_Right,)
BACKWARD_KEYS = (Qt.Key.Key_Left,)
# A control a caret lives in, whatever it is called. A read-only text view is
# not one of these: nothing is being typed into it, so the arrows are the
# ring's as everywhere else.
TYPED_INTO = (QLineEdit, QAbstractSpinBox)
EDITABLE = (QTextEdit, QPlainTextEdit)
# What the menu bar and its popups answer for themselves.
MENU_WIDGETS = (QMenuBar, QMenu)


def keeps_the_arrows(widget: QWidget) -> bool:
    """Whether this stop answers the horizontal keys itself."""
    if getattr(widget, "keeps_horizontal_keys", False):
        return True
    if isinstance(widget, MENU_WIDGETS + TYPED_INTO):
        return True
    return isinstance(widget, EDITABLE) and not widget.isReadOnly()


def holds_the_focus(widget: QWidget) -> bool:
    """Whether this widget is the one its own window has the focus on.

    Asked because a key nobody consumes is offered to the parent, then to ITS
    parent, all the way up: measured, a Right the library list declined
    arrived a second time addressed to the stack behind it; a ring stepped from
    there lands somewhere the keyboard never was. So the rule is that the
    receiver has to be the stop itself.

    Asked of the widget's own window rather than of the application, since a
    window that is shown without being activated has no application focus
    widget at all while its own focus is exactly where it was put.
    """
    window = widget.window()
    return window is not None and window.focusWidget() is widget


def is_a_stop(widget: QWidget, window: QWidget) -> bool:
    """Whether the ring should offer this widget, by the rules Tab uses.

    The same three questions Qt asks of a Tab press, plus the window, since a
    popup's own widgets sit in a focus chain of their own and are not stops on
    the window's ring.
    """
    if widget.window() is not window:
        return False
    if not widget.isEnabled() or not widget.isVisible():
        return False
    return bool(widget.focusPolicy() & Qt.FocusPolicy.TabFocus)


def next_stop(widget: QWidget, forward: bool) -> QWidget | None:
    """The stop a Tab press from here would reach; None when there is none.

    Walked along Qt's own focus chain rather than along a list kept beside it,
    so what the arrows reach and what Tab reaches cannot come to differ. The
    chain is a cycle, which is where the ring's wrap comes from; it is also
    why the walk carries a guard against coming back to where it started.
    """
    window = widget.window()
    seen: set[int] = set()
    current = widget
    while True:
        current = (
            current.nextInFocusChain() if forward else current.previousInFocusChain()
        )
        if current is None or current is widget or id(current) in seen:
            return None
        seen.add(id(current))
        if is_a_stop(current, window):
            return current


class ArrowRing(QObject):
    """Turns a Left or Right press into the Tab press it stands for."""

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        application = QApplication.instance()
        if application is not None:
            application.installEventFilter(self)

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        """Step the ring, unless the stop under the keyboard owns the key."""
        if event.type() is not QEvent.Type.KeyPress:
            return False
        if not isinstance(event, QKeyEvent):
            return False
        key = event.key()
        if key not in FORWARD_KEYS and key not in BACKWARD_KEYS:
            return False
        if event.modifiers() not in (
            Qt.KeyboardModifier.NoModifier,
            Qt.KeyboardModifier.KeypadModifier,
        ):
            return False
        return self.step(watched, key in FORWARD_KEYS)

    def step(self, focused: QObject, forward: bool) -> bool:
        """Move the ring one stop; False leaves the key to whatever had it.

        The stop is the object the key was DELIVERED to, which has to be the
        widget its window holds the focus on: see `holds_the_focus`.

        A popup that is not a menu is shut on the way past, which is what
        makes the volume slider leavable: it lives in a window of its own, so
        it is on no ring at all and the button that opened it is the stop the
        ring is really standing on.
        """
        if not isinstance(focused, QWidget) or not holds_the_focus(focused):
            return False
        if keeps_the_arrows(focused):
            return False
        popup = QApplication.activePopupWidget()
        if popup is not None:
            if isinstance(popup, QMenu):
                return False
            popup.close()
            focused = QApplication.focusWidget()
            if not isinstance(focused, QWidget) or keeps_the_arrows(focused):
                return False
        going_to = next_stop(focused, forward)
        if going_to is None:
            return False
        going_to.setFocus(
            Qt.FocusReason.TabFocusReason
            if forward
            else Qt.FocusReason.BacktabFocusReason
        )
        return True
