"""What a finished scan found, said once in a dialog rather than in passing.

The status bar already carried a one-line total, which is the right weight for
something nobody asked for and the wrong weight for an answer somebody pressed
a button to get: it is gone from the screen a few seconds later; it cannot
say WHICH albums turned up. Somebody who has just added music to their folder
is asking what arrived, so that is what leads here.

The report is built as text apart from the dialog that shows it, so what it
says can be checked without a screen.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QTextBrowser, QVBoxLayout, QWidget

from stellody.application.scan import ScanReport
from stellody.domain.changes import LibraryChange
from stellody.domain.identity import AlbumIdentity
from stellody.ui.dialogs import NeutralDialog, close_row, icon_label
from stellody.ui.widgets import ReadingPane

# The dialog is sized against its own type rather than to a remembered pair of
# numbers, so doubling the text does not leave the report reading through a
# letterbox.
TEXT_SCALE = 2.0
DIALOG_WIDTH_PX = round(620 * TEXT_SCALE)
DIALOG_HEIGHT_PX = round(520 * TEXT_SCALE)
# The mark leads the dialog, so it is set well above the About dialog's, where
# it sits beside a body of text rather than above one.
MARK_PX = 128
MARK_MARGIN_PX = 12
# Enough to recognise what arrived without the dialog becoming the library.
MAX_ALBUMS_SHOWN = 20


def _escape(value: str) -> str:
    """Make a title safe to place inside the report's markup."""
    return value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _plural(count: int, one: str, many: str) -> str:
    """A count with the word that suits it, so nothing reads as 1 albums."""
    return f"{count} {one if count == 1 else many}"


def _album_list(identities: tuple[AlbumIdentity, ...]) -> str:
    """The albums themselves, capped, with the remainder counted rather than cut."""
    shown = identities[:MAX_ALBUMS_SHOWN]
    rows = "".join(
        f"<li>{_escape(identity.title)} "
        f"<i>by {_escape(identity.album_artist)}</i></li>"
        for identity in shown
    )
    rest = len(identities) - len(shown)
    tail = f"<li><i>and {_plural(rest, 'other', 'others')}</i></li>" if rest else ""
    return f"<ul>{rows}{tail}</ul>"


def _headline(change: LibraryChange) -> str:
    """The first thing read, which is the answer to why the button was pressed."""
    if change.is_first_reading:
        return (
            f"<p>Your library is in: {_plural(change.total_albums, 'album', 'albums')}"
            f", {_plural(change.total_tracks, 'track', 'tracks')}.</p>"
        )
    if change.nothing_changed:
        return "<p>Nothing has changed since the last scan.</p>"
    parts = []
    if change.new_albums:
        parts.append(f"{_plural(len(change.new_albums), 'new album', 'new albums')}")
    if change.new_tracks:
        parts.append(f"{_plural(change.new_tracks, 'new track', 'new tracks')}")
    if change.gone_albums:
        parts.append(f"{_plural(len(change.gone_albums), 'album', 'albums')} gone")
    if change.gone_tracks:
        parts.append(f"{_plural(change.gone_tracks, 'track', 'tracks')} gone")
    return f"<p>{', '.join(parts)}.</p>"


def _table(rows: list[tuple[str, str]]) -> str:
    """One block of counts, each named for what it actually counts."""
    cells = "".join(
        f"<tr><td>{name}</td><td align='right'><b>{value}</b></td></tr>"
        for name, value in rows
    )
    return f"<table width='100%'>{cells}</table>"


def _totals(change: LibraryChange, report: ScanReport) -> str:
    """The library as it stands, then separately what the scan did to say so.

    The two were one table and it misled on both counts. The library's file
    count sat under a heading about the scan while wearing the label "Files
    read", which on a rescan that changed nothing named several thousand files
    that were never opened; and the folders were reported only as the ones
    re-read, so a scan that found everything unchanged said it had read nought
    folders, which reads as a scan that did nothing rather than as one with
    nothing to do.
    """
    library = _table(
        [
            ("Albums", str(change.total_albums)),
            ("Tracks", str(change.total_tracks)),
            ("Music files", str(report.files_in_library)),
        ]
    )
    work = [
        ("Folders checked", str(report.folders_checked)),
        ("Folders re-read", str(report.folders_probed)),
    ]
    if report.files_unreadable:
        work.append(("Files that could not be read", str(report.files_unreadable)))
    if report.files_absent:
        work.append(("Files no longer there", str(report.files_absent)))
    return (
        f"<h3>Your library now</h3>{library}"
        f"<h3>What this scan did</h3>{_table(work)}"
    )


def summary_html(change: LibraryChange, report: ScanReport) -> str:
    """The whole report, as the dialog shows it."""
    body = ["<h2>Scan finished</h2>", _headline(change)]
    if change.new_albums:
        body.append("<h3>New albums</h3>")
        body.append(_album_list(change.new_albums))
    if change.gone_albums:
        body.append("<h3>Albums no longer found</h3>")
        body.append(
            "<p>These were in your library and are not now. An unplugged drive "
            "or a folder renamed on disk both read this way; nothing has been "
            "deleted.</p>"
        )
        body.append(_album_list(change.gone_albums))
    body.append(_totals(change, report))
    if report.issues:
        body.append(
            f"<p>{_plural(len(report.issues), 'labelling issue', 'labelling issues')} "
            "found. Help then Library health lists them; your files are "
            "untouched either way.</p>"
        )
    return "".join(body)


class ScanSummaryDialog(NeutralDialog):
    """Shows what a finished scan found."""

    def __init__(
        self,
        change: LibraryChange,
        report: ScanReport,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Scan finished")
        self.resize(DIALOG_WIDTH_PX, DIALOG_HEIGHT_PX)
        layout = QVBoxLayout(self)
        self.badge = icon_label(self, MARK_PX)
        if self.badge is not None:
            layout.addSpacing(MARK_MARGIN_PX)
            layout.addWidget(self.badge, alignment=Qt.AlignmentFlag.AlignHCenter)
            layout.addSpacing(MARK_MARGIN_PX)
        body = QTextBrowser(self)
        # Measured after polish, never before: a fresh widget still carries the
        # fallback font, so scaling what it reports then would scale the wrong
        # number. Setting the widget's font rather than a size in the markup
        # keeps every heading in proportion with the text under it.
        body.ensurePolished()
        font = body.font()
        font.setPointSizeF(font.pointSizeF() * TEXT_SCALE)
        body.setFont(font)
        body.setHtml(summary_html(change, report))
        layout.addWidget(body)
        layout.addLayout(close_row(self))
        self.pane = ReadingPane(body)
