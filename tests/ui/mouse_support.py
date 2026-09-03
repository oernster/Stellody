"""Building a mouse press Qt does not call deprecated.

The short form, `QMouseEvent(type, localPos, button, buttons, modifiers)`, is
marked deprecated in PySide6 and warned on every use: measured here, it raises
a DeprecationWarning while the form taking a global position raises none and
reports the same `position()`. Two test files were each constructing the short
form by hand, so the warning arrived four times a run and the fix would have
had to be made twice.

Offscreen there is no screen to be global to, so the two points are the same
one. Nothing under test reads the global position; what is being exercised is
where along a control the press landed.
"""

from __future__ import annotations

from PySide6.QtCore import QEvent, QPointF, Qt
from PySide6.QtGui import QMouseEvent


def press_at(
    where: QPointF, button: Qt.MouseButton = Qt.MouseButton.LeftButton
) -> QMouseEvent:
    """A press of `button` at `where`, in the form Qt still wants."""
    return QMouseEvent(
        QEvent.Type.MouseButtonPress,
        where,
        where,
        button,
        button,
        Qt.KeyboardModifier.NoModifier,
    )
