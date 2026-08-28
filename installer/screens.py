"""How each screen of the setup program is put together.

The window owns the controls and decides what is said; this module owns how a
screen is laid out, so the two concerns can be read apart. Every builder takes
the controls it arranges rather than reaching for them, which keeps the window
the only thing that holds state.
"""

from __future__ import annotations

from collections.abc import Iterable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QFrame,
    QLabel,
    QProgressBar,
    QVBoxLayout,
    QWidget,
)

from installer import theme

HINT_INDENT_PX = theme.CHECK_PX + theme.OPTION_GAP_PX + 7
HEADING_GAP_PX = 7
LEAD_GAP_PX = 16
TRACK_GAP_PX = 9


def rule(parent: QWidget) -> QFrame:
    """The hairline that separates the header and the footer from the body."""
    line = QFrame(parent)
    line.setObjectName("Rule")
    line.setFixedHeight(1)
    return line


def label(parent: QWidget, text: str, name: str) -> QLabel:
    """One styled line of text."""
    made = QLabel(text, parent)
    made.setObjectName(name)
    made.setWordWrap(True)
    return made


def _column(parent: QWidget, centred: bool = False) -> tuple[QWidget, QVBoxLayout]:
    """A bare screen and its column, with no margins of its own.

    A centred column holds its content together in the middle of the body
    rather than letting the stack stretch the gaps between its lines apart.
    """
    screen = QWidget(parent)
    column = QVBoxLayout(screen)
    column.setContentsMargins(0, 0, 0, 0)
    column.setSpacing(0)
    if centred:
        column.addStretch()
    return screen, column


def option(parent: QWidget, box: QCheckBox, hint: str) -> QWidget:
    """One choice, with the muted line that explains it underneath."""
    holder, column = _column(parent)
    column.addWidget(box)
    if hint:
        note = label(holder, hint, "Hint")
        note.setContentsMargins(HINT_INDENT_PX, 0, 0, 0)
        column.addWidget(note)
    return holder


def choices(
    parent: QWidget,
    heading: str,
    lead: str,
    location: str,
    options: Iterable[tuple[QCheckBox, str]],
) -> QWidget:
    """What setup is about to do, plus the choices that shape it."""
    screen, column = _column(parent, centred=True)
    column.addWidget(label(screen, heading, "Heading"))
    column.addSpacing(HEADING_GAP_PX)
    column.addWidget(label(screen, lead, "Lead"))
    column.addSpacing(LEAD_GAP_PX)
    if not location:
        column.addStretch()
        return screen
    column.addWidget(label(screen, f"Install location<br>{location}", "InfoBox"))
    for box, hint in options:
        column.addSpacing(theme.OPTION_SPACING_PX)
        column.addWidget(option(screen, box, hint))
    column.addStretch()
    return screen


def progress(
    parent: QWidget, title: QLabel, bar: QProgressBar, status: QLabel
) -> QWidget:
    """What is happening now, with the bar that says how far in it is."""
    screen, column = _column(parent, centred=True)
    column.addWidget(title)
    column.addSpacing(LEAD_GAP_PX)
    column.addWidget(bar)
    column.addSpacing(TRACK_GAP_PX)
    column.addWidget(status)
    column.addStretch()
    return screen


def verdict(parent: QWidget, mark: QLabel, title: QLabel, lead: QLabel) -> QWidget:
    """How it ended, centred, as one mark and two lines."""
    screen, column = _column(parent, centred=True)
    for widget in (mark, title, lead):
        widget.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        column.addWidget(widget)
    column.addStretch()
    return screen
