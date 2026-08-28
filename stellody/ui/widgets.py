"""Small shared widget helpers."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtWidgets import QHBoxLayout, QPushButton, QWidget


def choice_row(
    parent: QWidget,
    primary: tuple[str, Callable[[], None]],
    secondary: tuple[str, Callable[[], None]],
) -> QHBoxLayout:
    """A trailing row of two buttons, the primary one focused and default."""
    row = QHBoxLayout()
    row.addStretch()
    secondary_button = QPushButton(secondary[0], parent)
    secondary_button.clicked.connect(secondary[1])
    row.addWidget(secondary_button)
    primary_button = QPushButton(primary[0], parent)
    primary_button.setDefault(True)
    primary_button.clicked.connect(primary[1])
    row.addWidget(primary_button)
    return row
