"""The library health view: what Stellody worked around, reported not repaired."""

from __future__ import annotations

from PySide6.QtWidgets import QTextBrowser, QVBoxLayout, QWidget

from stellody.domain.health import IssueKind, LibraryIssue, issue_counts, sorted_issues
from stellody.ui.dialogs import NeutralDialog, close_row
from stellody.ui.display import native_path

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


class HealthDialog(NeutralDialog):
    """Shows the library health report."""

    def __init__(
        self, issues: tuple[LibraryIssue, ...], parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Library health")
        self.resize(DIALOG_WIDTH_PX, DIALOG_HEIGHT_PX)
        layout = QVBoxLayout(self)
        body = QTextBrowser(self)
        body.setHtml(report_html(issues))
        layout.addWidget(body)
        layout.addLayout(close_row(self))
