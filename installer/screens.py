"""How each screen of the setup program is put together.

The window owns the controls and decides what is said; this module owns how a
screen is laid out, so the two concerns can be read apart. Every builder takes
the controls it arranges rather than reaching for them, which keeps the window
the only thing that holds state.
"""

from __future__ import annotations

from collections.abc import Iterable

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from installer import theme, wording

HINT_INDENT_PX = theme.CHECK_PX + theme.OPTION_GAP_PX + 7
HEADING_GAP_PX = 7
LEAD_GAP_PX = 16
TRACK_GAP_PX = 9


def header(
    parent: QWidget,
    title: str,
    tagline: str,
    icon_path,
    controls: Iterable[QPushButton],
) -> QHBoxLayout:
    """The identity, drawn at a size that can be read across the room.

    The mark, then the name over its tagline, then the controls at the right.
    The version is not here: it belongs in the heading of the screen talking
    about it.
    """
    row = QHBoxLayout()
    row.setSpacing(theme.HEADER_GAP_PX)
    if icon_path is not None:
        mark = QLabel(parent)
        mark.setPixmap(
            QIcon(str(icon_path)).pixmap(QSize(theme.MARK_PX, theme.MARK_PX))
        )
        mark.setFixedSize(theme.MARK_PX, theme.MARK_PX)
        row.addWidget(mark, alignment=Qt.AlignmentFlag.AlignVCenter)
    who = QVBoxLayout()
    who.setSpacing(0)
    name = label(parent, title, "HeaderTitle")
    # The product name never breaks across two lines, whatever shares the row.
    name.setWordWrap(False)
    who.addWidget(name)
    who.addWidget(label(parent, tagline, "HeaderSub"))
    row.addLayout(who, 1)
    for control in controls:
        row.addWidget(control, alignment=Qt.AlignmentFlag.AlignVCenter)
    return row


def footer(parent: QWidget, buttons: Iterable[QPushButton]) -> QHBoxLayout:
    """The actions, right aligned, under a rule."""
    row = QHBoxLayout()
    row.setSpacing(theme.FOOTER_GAP_PX)
    row.addStretch()
    for button in buttons:
        row.addWidget(button)
    return row


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


def install_choices(
    parent: QWidget,
    heading: str,
    lead: str,
    location: str,
    boxes: tuple[QCheckBox, QCheckBox, QCheckBox, QCheckBox],
) -> QWidget:
    """The opening screen of an install, with its four options set up.

    Starting in the tray only means something once starting at sign-in is
    chosen, so it follows that box rather than standing on its own.
    """
    desktop, start_menu, sign_in, minimised = boxes
    desktop.setChecked(True)
    start_menu.setChecked(True)
    sign_in.toggled.connect(minimised.setEnabled)
    minimised.setEnabled(False)
    options = (
        (desktop, ""),
        (start_menu, ""),
        (sign_in, wording.SIGN_IN_HINT),
        (minimised, wording.MINIMISED_HINT),
    )
    return choices(parent, heading, lead, location, options)


def message(parent: QWidget, heading: str, lead: str) -> QWidget:
    """A screen that only has something to say, such as the app being open."""
    screen, column = _column(parent, centred=True)
    column.addWidget(label(screen, heading, "Heading"))
    column.addSpacing(HEADING_GAP_PX)
    column.addWidget(label(screen, lead, "Lead"))
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
