"""The single row beneath the answer: the ticks, the pages, then the way out.

**One row rather than two.** Reported by Oliver on 2026-09-09 against the
shipped screen: the pager stood on a row of its own above the row carrying
Copy, Find in shops and Close, so the foot of the dialog read as two feet. The
way through the answer and the way out of it belong on the same line.

The pager carries a stretch on each side of itself, so dropping it between the
controls that act on the ticks and the one that leaves is what centres it. No
stretch is added beside it here; a second one would push it off centre.

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
# Said on the copy control once it has been pressed, so a press that changed
# nothing visible is still a press somebody saw work.
COPIED = "Copied"
# What the two controls carry, both Oliver's own artwork. A control whose
# picture is missing keeps its words rather than becoming a blank square.
SHOP_ICON = "shop.png"
COPY_ICON = "copy.png"


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


def foot_row(
    parent: QWidget,
    pager: QWidget,
    copy_ticked: Callable[[], None],
    open_shops: Callable[[], None],
    leave: Callable[[], None],
) -> tuple[QHBoxLayout, QPushButton, QPushButton, QPushButton]:
    """The row itself, with the three controls standing in it."""
    row = QHBoxLayout()
    copy_button = control(COPY_LABEL, COPY_ICON, copy_ticked, parent)
    row.addWidget(copy_button)
    shops_button = control(SHOPS_LABEL, SHOP_ICON, open_shops, parent)
    row.addWidget(shops_button)
    row.addWidget(pager)
    close_button = wearing(
        QPushButton(CLOSE_LABEL, parent), resources.find_asset(CLOSE_ICON)
    )
    close_button.setDefault(True)
    close_button.clicked.connect(leave)
    row.addWidget(close_button)
    return row, copy_button, shops_button, close_button
