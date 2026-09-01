"""The pieces both trays are built from.

The strip along the top and the strip along the bottom draw the same kind of
control at two sizes, so the button is written once and told how large to be
rather than written twice and kept in step by hand. The hairline that rules one
group off from the next is here for the same reason.
"""

from __future__ import annotations

import pathlib
from collections.abc import Callable

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QFrame, QPushButton, QWidget


def icon_button(
    parent: QWidget,
    path: pathlib.Path | None,
    tip: str,
    on_click: Callable[[], None],
    button_px: int,
    icon_px: int,
) -> QPushButton:
    """One picture-only button, sized to its artwork.

    A button with no artwork yet is still built: several of these are given
    their picture later, by whatever knows which state they are showing.
    """
    button = QPushButton(parent)
    button.setObjectName("TrayButton")
    button.setToolTip(tip)
    button.setFixedSize(button_px, button_px)
    button.setIconSize(QSize(icon_px, icon_px))
    if path is not None:
        button.setIcon(QIcon(str(path)))
    button.clicked.connect(on_click)
    return button


def separator(parent: QWidget, width_px: int, height_px: int) -> QFrame:
    """The hairline ruling one group of buttons off from the next.

    Drawn as a plain frame carrying a background rather than as a Qt VLine,
    because a VLine takes its colour from the palette and this one has to take
    it from the appearance the application is wearing.
    """
    line = QFrame(parent)
    line.setObjectName("TraySeparator")
    line.setFrameShape(QFrame.Shape.NoFrame)
    line.setFocusPolicy(Qt.FocusPolicy.NoFocus)
    line.setFixedSize(width_px, height_px)
    return line
