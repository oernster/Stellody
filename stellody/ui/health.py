"""The library health view: what Stellody worked around, reported not repaired."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QSize
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QHBoxLayout,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from stellody.domain.health import IssueKind, LibraryIssue, issue_counts, sorted_issues
from stellody.shared import resources
from stellody.ui.bottom_tray import BOTTOM_BUTTON_PX, BOTTOM_ICON_PX, REPAIR_TOOLTIP
from stellody.ui.dialogs import NeutralDialog, close_row
from stellody.ui.display import native_path
from stellody.ui.widgets import ReadingPane

DIALOG_WIDTH_PX = 760
DIALOG_HEIGHT_PX = 560
MAX_PATHS_SHOWN = 12

CLEAN_MESSAGE = (
    "<h2>Library health</h2>"
    "<p>Nothing needed working around. Every track's disc number, track "
    "number and title came straight from its tags.</p>"
)

PREAMBLE = (
    "<h2>Library health</h2>"
    "<p>Stellody never writes to your music files, so nothing below has been "
    "repaired. Each entry says what the tags claimed and what Stellody used "
    "instead, so you can fix them in a tagger of your choosing.</p>"
)


def _escape(value: str) -> str:
    """Make a filename safe to place inside the report's markup."""
    return value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _paths_html(issue: LibraryIssue) -> str:
    """The affected files, truncated with an honest note when there are many."""
    if not issue.paths:
        return ""
    shown = issue.paths[:MAX_PATHS_SHOWN]
    items = "".join(f"<li>{_escape(native_path(path))}</li>" for path in shown)
    remainder = len(issue.paths) - len(shown)
    if remainder > 0:
        items += f"<li><i>and {remainder} more</i></li>"
    return f"<ul>{items}</ul>"


def _summary_html(issues: tuple[LibraryIssue, ...]) -> str:
    """A count of each kind of issue found."""
    counts = issue_counts(issues)
    rows = "".join(
        f"<tr><td>{_escape(str(kind))}</td><td align='right'>{count}</td></tr>"
        for kind, count in sorted(counts.items(), key=lambda item: str(item[0]))
    )
    return (
        "<table width='100%' cellpadding='3'>"
        f"<tr><th align='left'>Issue</th><th align='right'>Count</th></tr>"
        f"{rows}</table><hr>"
    )


def _issue_html(issue: LibraryIssue) -> str:
    """One issue as a heading, an explanation and its files."""
    detail = f" ({_escape(issue.detail)})" if issue.detail else ""
    return (
        f"<p><b>{_escape(issue.album)}</b>{detail}<br>"
        f"<i>{_escape(issue.summary)}</i></p>"
        f"{_paths_html(issue)}"
    )


def report_html(issues: tuple[LibraryIssue, ...]) -> str:
    """The whole health report."""
    if not issues:
        return CLEAN_MESSAGE
    ordered = sorted_issues(issues)
    body = "".join(_issue_html(issue) for issue in ordered)
    return PREAMBLE + _summary_html(ordered) + body


def has_serious_issues(issues: tuple[LibraryIssue, ...]) -> bool:
    """True when something worth surfacing on the status bar was found."""
    serious = {
        IssueKind.DUPLICATE_TRACK_NUMBER,
        IssueKind.DISC_NUMBER_CONFLICT,
        IssueKind.UNREADABLE_FILE,
    }
    return any(issue.kind in serious for issue in issues)


def _repair_button(parent: QWidget, on_click: Callable[[], None]) -> QPushButton:
    """The repair control, drawn at the smaller of the two tray sizes.

    Small because it sits in a dialog rather than in the tray under the menus,
    where the one it mirrors is.

    Disabled for the same reason that one is: what each issue
    should become is already worked out on every load; there is nowhere yet
    to keep a correction once it has been accepted.
    """
    button = QPushButton(parent)
    button.setObjectName("TrayButton")
    button.setToolTip(REPAIR_TOOLTIP)
    button.setFixedSize(BOTTOM_BUTTON_PX, BOTTOM_BUTTON_PX)
    button.setIconSize(QSize(BOTTOM_ICON_PX, BOTTOM_ICON_PX))
    path = resources.library_health_icon_path()
    if path is not None:
        button.setIcon(QIcon(str(path)))
    button.clicked.connect(on_click)
    button.setEnabled(False)
    return button


class HealthDialog(NeutralDialog):
    """Shows the library health report."""

    def __init__(
        self,
        issues: tuple[LibraryIssue, ...],
        parent: QWidget | None = None,
        repair_library: Callable[[], None] = lambda: None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Library health")
        self.resize(DIALOG_WIDTH_PX, DIALOG_HEIGHT_PX)
        layout = QVBoxLayout(self)
        # Above the report rather than inside it, so the report is the only
        # thing that scrolls and the repair button stays where it was put.
        self.repair_button = _repair_button(self, repair_library)
        heading = QHBoxLayout()
        heading.addWidget(self.repair_button)
        heading.addStretch()
        layout.addLayout(heading)
        body = QTextBrowser(self)
        body.setHtml(report_html(issues))
        layout.addWidget(body)
        layout.addLayout(close_row(self))
        self.pane = ReadingPane(body)
