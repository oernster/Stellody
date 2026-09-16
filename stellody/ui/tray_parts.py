"""The pieces both trays are built from.

The strip along the top and the strip along the bottom draw the same kind of
control at two sizes, so the button is written once and told how large to be
rather than written twice and kept in step by hand. The hairline that rules one
group off from the next is here for the same reason, as is the row that holds
one thing at the middle of a strip between two groups.
"""

from __future__ import annotations

import pathlib
from collections.abc import Callable

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QBoxLayout,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QPushButton,
    QWidget,
)

LEFT_COLUMN = 0
MIDDLE_COLUMN = 1
RIGHT_COLUMN = 2
# The two outer columns take the same share of what is spare.
EQUAL_SHARE = 1


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
    # The ring belongs to the keyboard. Qt gives a button StrongFocus, which
    # takes the focus on a click as well as on Tab, so a pressed button kept
    # the ring afterwards with the pointer nowhere near it: measured on
    # 2026-09-08 as hasFocus True with underMouse False. Reported as the icon
    # wearing a green rectangle it had not earned. Tab focus alone leaves it a
    # stop on the ring without a press ever painting one.
    button.setFocusPolicy(Qt.FocusPolicy.TabFocus)
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


def group(gap_px: int, *widgets: QWidget) -> QHBoxLayout:
    """Widgets side by side with the strip's gap between them and no margin."""
    row = QHBoxLayout()
    row.setContentsMargins(0, 0, 0, 0)
    row.setSpacing(gap_px)
    for widget in widgets:
        row.addWidget(widget)
    return row


def centred_row(
    parent: QWidget,
    margin_px: int,
    gap_px: int,
    left: QBoxLayout,
    middle: QBoxLayout,
    right: QBoxLayout,
) -> QGridLayout:
    """Hold `middle` at the middle of the strip, whatever the two ends weigh.

    A stretch either side of the middle centres it in what the two end groups
    leave OVER, which is the middle of the strip only while those groups are
    the same width. They seldom are: that is what put the bottom strip's
    visualiser off centre, then the top tray's transport, reported left of
    centre on a 13 inch 4K screen on 2026-09-16.

    Three columns instead, with the outer two given the same share of what is
    spare. That puts the middle at the middle while there is room; where there
    is not, each column keeps its own content and the middle drifts rather than
    being sat on. Measured on the bottom strip, laying all three in ONE cell
    centres exactly at every width but lets a group overlap the middle below
    about 1100 pixels.
    """
    row = QGridLayout(parent)
    row.setContentsMargins(margin_px, margin_px, margin_px, margin_px)
    row.setSpacing(gap_px)
    row.setColumnStretch(LEFT_COLUMN, EQUAL_SHARE)
    row.setColumnStretch(RIGHT_COLUMN, EQUAL_SHARE)
    across = Qt.AlignmentFlag.AlignVCenter
    row.addLayout(left, 0, LEFT_COLUMN, Qt.AlignmentFlag.AlignLeft | across)
    row.addLayout(middle, 0, MIDDLE_COLUMN, across)
    row.addLayout(right, 0, RIGHT_COLUMN, Qt.AlignmentFlag.AlignRight | across)
    return row
