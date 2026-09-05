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

from math import ceil

from PySide6.QtCore import Qt
from PySide6.QtGui import QTextDocument
from PySide6.QtWidgets import QTextBrowser, QVBoxLayout, QWidget

from stellody.application.scan import ScanReport
from stellody.domain.changes import LibraryChange
from stellody.domain.identity import AlbumIdentity
from stellody.ui.dialogs import FirstStopDialog, close_row, icon_label
from stellody.ui.widgets import ReadingPane

TEXT_SCALE = 1.5
# Neither dimension is chosen; both are measured against the report itself.
# The widest the text may be, which is a line an eye still tracks back
# comfortably at this size rather than the widest that would fit a screen. A
# report whose longest line is shorter than this takes only what it uses.
MAX_TEXT_WIDTH_PX = 674
# Below this the mark and the Close button decide the width anyway, so a very
# short report is not squeezed into a slot narrower than its own furniture.
MIN_TEXT_WIDTH_PX = 360
# The height is NOT chosen. A scan that changed nothing says so in six lines
# and a scan that found twenty albums needs twenty more, so a fixed height is
# either a cramped page or (as it was) a great deal of empty dialog under a
# short report. The dialog is measured against what it actually holds and
# stops growing here, beyond which the page scrolls instead.
MAX_BODY_HEIGHT_PX = round(520 * TEXT_SCALE)
# Breathing room under the last line, so the report does not end flush against
# the frame. The frame itself is asked for at measuring time rather than
# guessed, since the style decides it.
BODY_PADDING_PX = 8
# The gap between a label and its figure. At full width the table threw every
# number against the right edge, which left Albums an inch and a half from 502.
VALUE_GAP_PX = 28


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
    """One block of counts, each named for what it actually counts.

    Sized to its own content rather than to the dialog. At full width every
    number was thrown against the right edge, so a short label like Albums sat
    an inch and a half from its own figure and the eye had to travel the gap to
    pair them up. The middle cell is that gap, made a deliberate small one; the
    numbers stay right aligned so their digits line up down the column.
    """
    cells = "".join(
        f"<tr><td>{name}</td>"
        f"<td width='{VALUE_GAP_PX}'></td>"
        f"<td align='right'><b>{value}</b></td></tr>"
        for name, value in rows
    )
    return f"<table cellspacing='0' cellpadding='0'>{cells}</table>"


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
            "found. Help then Library health lists them.<br>"
            "Your files are untouched either way.</p>"
        )
    return "".join(body)


class ScanSummaryDialog(FirstStopDialog):
    """Shows what a finished scan found."""

    def __init__(
        self,
        change: LibraryChange,
        report: ScanReport,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Scan finished")
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
        self._fit_to_report(body)

    def _fit_to_report(self, body: QTextBrowser) -> None:
        """Size the dialog to the report rather than to a remembered number.

        The measurement is taken on a document of its own rather than on the
        one inside the view. Setting a text width on the view's document does
        not hold: the widget puts its own viewport width back. A widget
        that has not been shown yet is a few dozen pixels wide, so it reported
        a page 1853 pixels tall against the 278 it really is and every report
        came out clamped to the ceiling. A detached document laid out at the
        width the text will be read at cannot be overruled that way.

        The clamp then STAYS: releasing it after measuring was tried and the
        page simply grew back to fill the dialog on show, which is the empty
        space this exists to remove. A report taller than the cap keeps the cap
        and scrolls, so the pane is a tab stop exactly when there is something
        below the fold, which is the rule it already followed.

        The width is measured the same way and in the same pass. The page is
        laid out at the widest it may be, then asked what width it actually
        used: a report whose longest line is a sentence of sixty characters
        wants nothing like the full measure; giving it the full measure
        left a third of the dialog empty to the right of every line.
        """
        measured = QTextDocument()
        measured.setDefaultFont(body.font())
        measured.setHtml(body.toHtml())
        measured.setTextWidth(MAX_TEXT_WIDTH_PX)
        used = max(
            MIN_TEXT_WIDTH_PX, min(ceil(measured.idealWidth()), MAX_TEXT_WIDTH_PX)
        )
        # Measured once. A second pass was tried, on the reasoning that a
        # narrowed page rewraps shorter. It moved nothing: once a text
        # width is set the document reports that width back as its ideal, so
        # the pass was a full layout that could never narrow anything.
        # Laid out again at the width it will really be read at, since a
        # narrower page wraps more and is therefore taller than the first
        # measurement said.
        measured.setTextWidth(used)
        # The view is made wider than the text by its own frame, because what
        # wraps the text is the VIEWPORT rather than the widget. Giving the
        # widget the measured width left the viewport narrower than the width
        # the height was measured at (618 against 620, measured), which lets a
        # line wrap that had not wrapped in the measurement and puts the report
        # over the height it was given. The frame is asked for rather than
        # assumed, since it is the style that decides it.
        frame = 2 * body.frameWidth()
        wanted = ceil(measured.size().height()) + frame + BODY_PADDING_PX
        fitted = min(wanted, MAX_BODY_HEIGHT_PX)
        # The page is fixed and the dialog is asked to fit it, rather than the
        # dialog being fixed and the page left to fill it. Setting the width on
        # the dialog would clip whenever the mark or the Close row needs more
        # than the text does, which is exactly the case a short report makes.
        body.setFixedSize(used + frame, fitted)
        self.layout().activate()
        self.adjustSize()
