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
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QWidget,
)

from installer import theme
from installer.shell import column, label, option

# Which screen is which in the window's stack. The order is the order they are
# added; naming them here keeps the window and the work half agreeing on it.
SCREEN_ROUTE = 0
SCREEN_UNINSTALL = 1
SCREEN_RUNNING = 2
SCREEN_PROGRESS = 3
SCREEN_VERDICT = 4

HEADING_GAP_PX = 7
LEAD_GAP_PX = 16
TRACK_GAP_PX = 9
FLOW_GAP_PX = 11
ARROW = "→"

Options = Iterable[tuple[QCheckBox, str]]


def flow(parent: QWidget, leaving: str, arriving: str) -> QWidget:
    """The two versions a change moves between, with the arrow between them.

    An update and a downgrade are about two versions, so neither goes in the
    heading: naming one there leaves the other unsaid or contradicts it.
    """
    holder = QWidget(parent)
    holder.setObjectName("Pane")
    row = QHBoxLayout(holder)
    row.setContentsMargins(0, 0, 0, 0)
    row.setSpacing(FLOW_GAP_PX)
    for text, name in (
        (leaving, "FlowFrom"),
        (ARROW, "FlowArrow"),
        (arriving, "FlowTo"),
    ):
        row.addWidget(label(holder, text, name))
    row.addStretch()
    return holder


def choices(
    parent: QWidget,
    heading: str,
    lead: str,
    options: Options,
    location: str = "",
    versions: tuple[str, str] | None = None,
) -> QWidget:
    """What setup is about to do, plus the choices that shape it."""
    screen, made = column(parent, centred=True)
    made.addWidget(label(screen, heading, "Heading"))
    made.addSpacing(HEADING_GAP_PX)
    made.addWidget(label(screen, lead, "Lead"))
    made.addSpacing(LEAD_GAP_PX)
    if versions is not None:
        made.addWidget(flow(screen, *versions))
        made.addSpacing(LEAD_GAP_PX)
    if location:
        made.addWidget(label(screen, f"Install location<br>{location}", "InfoBox"))
    for box, hint in options:
        made.addSpacing(theme.OPTION_SPACING_PX)
        made.addWidget(option(screen, box, hint))
    made.addStretch()
    return screen


def message(parent: QWidget, heading: str, lead: str) -> QWidget:
    """A screen that only has something to say, such as the app being open."""
    screen, made = column(parent, centred=True)
    made.addWidget(label(screen, heading, "Heading"))
    made.addSpacing(HEADING_GAP_PX)
    made.addWidget(label(screen, lead, "Lead"))
    made.addStretch()
    return screen


def progress(
    parent: QWidget, title: QLabel, bar: QProgressBar, status: QLabel
) -> QWidget:
    """What is happening now, with the bar that says how far in it is."""
    screen, made = column(parent, centred=True)
    made.addWidget(title)
    made.addSpacing(LEAD_GAP_PX)
    made.addWidget(bar)
    made.addSpacing(TRACK_GAP_PX)
    made.addWidget(status)
    made.addStretch()
    return screen


def verdict(parent: QWidget, mark: QLabel, title: QLabel, lead: QLabel) -> QWidget:
    """How it ended, centred, as one mark and two lines."""
    screen, made = column(parent, centred=True)
    for widget in (mark, title, lead):
        widget.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        made.addWidget(widget)
    made.addStretch()
    return screen
