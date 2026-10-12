"""Where a popup lifted from a button goes: above it where there is room.

Shared by the volume slider and the taste profiles list, the two popups that
are plain frames rather than menus. A menu is kept on the screen by Qt itself;
a frame is not, so this asks the screen the button is actually on, since a
second one may sit above or below the first.
"""

from __future__ import annotations

from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QWidget


def screen_top(widget: QWidget) -> int:
    """The top of the screen this widget is on, in screen coordinates."""
    handle = widget.screen() or QGuiApplication.primaryScreen()
    return handle.availableGeometry().top()


def lifted_top(height: int, button: QWidget) -> int:
    """The top of a popup this tall: above the button, else below it."""
    top = button.mapToGlobal(button.rect().topLeft())
    if top.y() - screen_top(button) >= height:
        return top.y() - height
    return button.mapToGlobal(button.rect().bottomLeft()).y()
