"""A control drawn as hovered is drawn again when the pointer leaves it.

Reported by Oliver on 2026-09-19: open the output list then press volume: the
output button kept its green ring beside the one volume had just earned.
Measured on the Windows platform with his own mouse, not reasoned: neither
button held the focus nor had the pointer over it, so the ring was a picture
nobody had redrawn. The button's last paint came while the pointer was over
it; its Leave then arrived with the list up; no HoverLeave and no paint
followed.

Qt asks for that paint on HoverLeave; it withholds HoverLeave from a
window while a popup of another window is up. The Leave still arrives, so it
is the Leave that asks for the paint here. Every widget whose style draws a
hover state is marked `WA_Hover`, which is exactly the set Qt would have sent
a HoverLeave to; this answers for all of them, the main window's and every
dialog's, with no list to keep up to date.
"""

from __future__ import annotations

from PySide6.QtCore import QEvent, QObject, Qt
from PySide6.QtWidgets import QApplication, QWidget


class LeaveRepaints(QObject):
    """Asks for a paint on a Leave that Qt will send no HoverLeave after."""

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        application = QApplication.instance()
        if application is not None:
            application.installEventFilter(self)

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        """Repaint a hover-drawn widget left while a popup is up; pass it on.

        With no popup Qt sends the HoverLeave itself, which already asks for
        the paint, so that case is left to it.
        """
        if event.type() is not QEvent.Type.Leave:
            return False
        if not isinstance(watched, QWidget):
            return False
        if not watched.testAttribute(Qt.WidgetAttribute.WA_Hover):
            return False
        if QApplication.activePopupWidget() is None:
            return False
        watched.update()
        return False
