"""A control drawn as hovered is drawn again when the pointer leaves it.

Reported by Oliver on 2026-09-19: open the output list then press volume: the
output button kept its green ring. Measured on the Windows platform with
his own mouse: the button's last paint came while the pointer was over it; its
Leave arrived with the list up; no HoverLeave and no paint ever followed. Qt
repaints a hovered control on HoverLeave and withholds that while a popup is
up, so the ring drawn on the way in stayed on the screen.

Offscreen cannot show the stale picture, since it repaints the window when a
popup opens. What it can show is the mechanism: a Leave that lands while a
popup is up asks for a paint. That is what these hold to.
"""

from __future__ import annotations

from output_support import choosing, devices
from playback_support import player, window
from PySide6.QtCore import QEvent, QObject, QPoint
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QMenu, QPushButton, QWidget

from stellody.ui.hover_paint import LeaveRepaints
from stellody.ui.output_menu import pop_up_above

__all__ = ["choosing", "devices", "player", "window"]

# Long enough for a popup to be shown and every paint it causes to be spent.
SETTLE_MS = 50


class _Paints(QObject):
    """Counts the paints one widget is given."""

    def __init__(self, widget: QWidget) -> None:
        super().__init__(widget)
        self.count = 0
        widget.installEventFilter(self)

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if event.type() is QEvent.Type.Paint:
            self.count += 1
        return False


def _hovered_button(holder: QWidget) -> QPushButton:
    """A shown button whose style draws something different on hover."""
    holder.setStyleSheet("QPushButton:hover { border: 2px solid green; }")
    button = QPushButton("hovered", holder)
    holder.show()
    QTest.qWaitForWindowExposed(holder)
    # Exposed is not finished: the show's last paint is still to come. It
    # would otherwise be counted against the Leave that happened to follow it.
    QTest.qWait(SETTLE_MS)
    return button


def _paints_after_leaving(button: QPushButton) -> int:
    """How many paints a Leave gets the button, with nothing else sent."""
    paints = _Paints(button)
    QApplication.sendEvent(button, QEvent(QEvent.Type.Leave))
    QTest.qWait(SETTLE_MS)
    return paints.count


def test_a_leave_under_a_popup_asks_for_a_paint(application) -> None:
    holder = QWidget()
    button = _hovered_button(holder)
    repaints = LeaveRepaints(holder)
    menu = QMenu(holder)
    menu.addAction("one")
    menu.popup(holder.mapToGlobal(QPoint(0, 0)))
    QTest.qWait(SETTLE_MS)
    assert QApplication.activePopupWidget() is menu

    assert _paints_after_leaving(button) > 0
    menu.hide()
    del repaints


def test_a_leave_with_no_popup_is_left_to_qt(application) -> None:
    """Qt sends HoverLeave itself then, which already asks for the paint."""
    holder = QWidget()
    button = _hovered_button(holder)
    repaints = LeaveRepaints(holder)
    assert QApplication.activePopupWidget() is None

    assert _paints_after_leaving(button) == 0
    del repaints


def test_the_window_repaints_the_output_button_under_its_list(choosing) -> None:
    """The case reported, through the window's own wiring."""
    sound = choosing._bottom_tray.sound
    choosing.show()
    QTest.qWaitForWindowExposed(choosing)
    pop_up_above(sound.output_menu, sound.output_button)
    QTest.qWait(SETTLE_MS)
    assert QApplication.activePopupWidget() is sound.output_menu

    assert _paints_after_leaving(sound.output_button) > 0
    sound.output_menu.hide()
