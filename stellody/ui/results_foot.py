"""The single row beneath the answer: the filter, the ticks, the pages, the way out.

**One row rather than two.** Reported by Oliver on 2026-09-09 against the
shipped screen: the pager stood on a row of its own above the row carrying
Copy, Find in shops and Close, so the foot of the dialog read as two feet. The
way through the answer and the way out of it belong on the same line.

**The pager stands on the middle of the dialog.** Asked for by Oliver on
2026-09-24: centred only between the controls on the left and Close, it sat
well right of the middle once Filter joined the left. `foot_row` says how.

**The Filter control leads the row.** Ruled by Oliver on 2026-09-13: it wears
the artwork the library's own filter wears; it is held down while a filter is
on, the way that one is. FR-D54.

This builds the row and hands back the controls in it. It is a builder rather
than a widget of its own on purpose: a widget would put the buttons one layout
deeper than the dialog's own column, which is a shape somebody reading the
dialog has to know about, for no gain.
"""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtWidgets import QHBoxLayout, QPushButton, QWidget

from stellody.shared import resources
from stellody.ui.dialogs import CLOSE_ICON, wearing

CLOSE_LABEL = "Close"
COPY_LABEL = "Copy"
SHOPS_LABEL = "Find in shops"
FILTER_LABEL = "Filter"
# Said on the copy control once it has been pressed, so a press that changed
# nothing visible is still a press somebody saw work.
COPIED = "Copied"
# What the two controls carry, both Oliver's own artwork. A control whose
# picture is missing keeps its words rather than becoming a blank square.
SHOP_ICON = "shop.png"
COPY_ICON = "copy.png"
# How the row's spare width is shared: both sides alike, the pager none, so
# the pager keeps its own width and the sides grow evenly around it.
SIDE_SHARE = 1
PAGER_SHARE = 0


def control(
    label: str, artwork: str, pressed: Callable[[], None], parent: QWidget
) -> QPushButton:
    """One control acting on the ticked albums, wearing its artwork.

    The words stay whatever the artwork does, since a picture-only button here
    would be two unlabelled squares under a list; the artwork is what makes
    them findable rather than what says what they do.
    """
    button = wearing(QPushButton(label, parent), resources.find_asset(artwork))
    button.setAutoDefault(False)
    button.clicked.connect(pressed)
    return button


def filter_control(parent: QWidget, pressed: Callable[[], None]) -> QPushButton:
    """The Filter control, checkable so a filter that is on holds it down.

    Clicked rather than toggled, since a press opens a chooser: whether the
    control ends up down is settled once that closes, by what was picked.
    """
    button = wearing(QPushButton(FILTER_LABEL, parent), resources.filter_icon_path())
    button.setCheckable(True)
    button.setAutoDefault(False)
    button.clicked.connect(pressed)
    return button


def foot_row(
    parent: QWidget,
    pager: QWidget,
    open_filter: Callable[[], None],
    copy_ticked: Callable[[], None],
    open_shops: Callable[[], None],
    leave: Callable[[], None],
) -> tuple[QHBoxLayout, QPushButton, QPushButton, QPushButton, QPushButton]:
    """The row itself, with the four controls standing in it.

    The controls on the left and Close on the right each stand in a side of
    their own; the two sides share whatever the pager leaves equally, so the
    pager stands on the middle of the dialog wherever the left side fits in
    half of what is left. Where it does not, the left side keeps its width and
    the pager stands as near the middle as that allows.
    """
    row = QHBoxLayout()
    left = QHBoxLayout()
    filter_button = filter_control(parent, open_filter)
    left.addWidget(filter_button)
    copy_button = control(COPY_LABEL, COPY_ICON, copy_ticked, parent)
    left.addWidget(copy_button)
    shops_button = control(SHOPS_LABEL, SHOP_ICON, open_shops, parent)
    left.addWidget(shops_button)
    left.addStretch()
    right = QHBoxLayout()
    right.addStretch()
    close_button = wearing(
        QPushButton(CLOSE_LABEL, parent), resources.find_asset(CLOSE_ICON)
    )
    close_button.setDefault(True)
    close_button.clicked.connect(leave)
    right.addWidget(close_button)
    row.addLayout(left, SIDE_SHARE)
    row.addWidget(pager, PAGER_SHARE)
    row.addLayout(right, SIDE_SHARE)
    return row, filter_button, copy_button, shops_button, close_button
