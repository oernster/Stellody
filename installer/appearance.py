"""Switching the setup program between the two palettes.

The toggle shows the appearance it would switch TO, which is why the icon is
chosen from the arriving mode rather than the current one.
"""

from __future__ import annotations

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QPushButton

from installer import theme
from stellody.shared import resources
from stellody.ui.theme import Mode


def toggle_icon_path(mode: Mode):
    """The artwork for the appearance the toggle would switch to."""
    arriving = theme.next_mode(mode)
    if arriving is Mode.LIGHT:
        return resources.light_mode_icon_path()
    return resources.dark_mode_icon_path()


def apply(mode: Mode, button: QPushButton) -> None:
    """Repaint the whole setup program, then re-face its toggle."""
    path = toggle_icon_path(mode)
    if path is not None:
        button.setIcon(QIcon(str(path)))
    button.setToolTip(f"Switch to the {theme.next_mode(mode).value} appearance")
    application = QApplication.instance()
    if application is not None:
        application.setStyleSheet(theme.installer_stylesheet(mode))
