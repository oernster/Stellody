"""A scrollable column of controls that is never itself a stop on the ring.

Shared by the repairs dialog and the taste profiles list. The controls inside
it are what a reader tabs to, so the area holding them has nothing of its own
to offer and takes no focus, nor does its viewport: a scroll area takes focus
from Tab and from a click by default, which is the rule every pane in this
application refuses.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QScrollArea, QVBoxLayout, QWidget


def scrolling_column(parent: QWidget) -> tuple[QScrollArea, QVBoxLayout]:
    """A scroll area taking no focus, with the column its controls go in."""
    area = QScrollArea(parent)
    area.setWidgetResizable(True)
    area.setFocusPolicy(Qt.FocusPolicy.NoFocus)
    area.viewport().setFocusPolicy(Qt.FocusPolicy.NoFocus)
    inner = QWidget(area)
    column = QVBoxLayout(inner)
    column.setContentsMargins(0, 0, 0, 0)
    area.setWidget(inner)
    return area, column
