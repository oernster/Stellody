"""The furniture every screen is drawn inside.

The header that never changes, the hairlines that bound the body and the small
pieces a screen is built from: a styled line of text, a bare column, one
choice with the note that explains it. The screens themselves are next door;
keeping the two apart is what lets a screen be read without also reading how a
label is styled.
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
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from installer import theme

HINT_INDENT_PX = theme.CHECK_PX + theme.OPTION_GAP_PX + 7


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


def column(parent: QWidget, centred: bool = False) -> tuple[QWidget, QVBoxLayout]:
    """A bare screen and its column, with no margins of its own.

    A centred column holds its content together in the middle of the body
    rather than letting the stack stretch the gaps between its lines apart.
    """
    screen = QWidget(parent)
    # Named so the stylesheet can leave it transparent; a pane painting the
    # flat window colour would cover the glow the window draws behind it.
    screen.setObjectName("Pane")
    made = QVBoxLayout(screen)
    made.setContentsMargins(0, 0, 0, 0)
    made.setSpacing(0)
    if centred:
        made.addStretch()
    return screen, made


def option(parent: QWidget, box: QCheckBox, hint: str) -> QWidget:
    """One choice, with the muted line that explains it underneath."""
    holder, made = column(parent)
    made.addWidget(box)
    if hint:
        note = label(holder, hint, "Hint")
        note.setContentsMargins(HINT_INDENT_PX, 0, 0, 0)
        made.addWidget(note)
    return holder
