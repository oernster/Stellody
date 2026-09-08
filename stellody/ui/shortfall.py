"""What a discovery run could not answer, said in the bar and listed on demand.

A run walks the artists somebody ticked genres for and asks two catalogues
about each. Three of those questions can end without a usable answer: the
source refuses, the catalogue does not know the name at all or it knows several
artists by that name. `RunReport` has carried all three since it was written,
in its own words because an artist nobody could look up is exactly the artist
somebody would otherwise assume had nothing missing. Nothing read them back,
so a run that failed on a third of a library said exactly what a clean one
said.

**Two weights, deliberately.** The bar carries the counts, which is the right
weight for something nobody asked for; the names are a dialog behind a button,
which is the right weight for an answer somebody pressed for. The same split
`scan_summary` makes, for the same reason.

**The button carries its own count** rather than relying on the sentence beside
it. The status bar is shared: playing a track replaces the text seconds later,
which would leave a button saying `Show them` next to a sentence about
something else entirely. A button reading `9 artists unanswered` still says
what it is once its sentence has gone.

The words and the report are built here as text, apart from any widget, so
what they say can be checked without a screen.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QPushButton, QTextBrowser, QVBoxLayout, QWidget

from stellody.application.values import RunReport
from stellody.ui.dialogs import FirstStopDialog, close_row
from stellody.ui.widgets import ReadingPane
from stellody.ui.words import ONE, escaped, plural

# Each group's clause for the status sentence, singular and plural. The
# ambiguous and unrecognised ones count NAMES rather than artists, which is
# what they are actually about: the catalogue answered, the name just did not
# settle on one artist.
COULD_NOT_ASK = (
    "one artist could not be asked about",
    "{count} artists could not be asked about",
)
NOT_RECOGNISED = ("one name was not recognised", "{count} names were not recognised")
MATCHED_SEVERAL = (
    "one name matched more than one artist",
    "{count} names matched more than one artist",
)
# Why the counts are worth reading at all, said once at the end however many
# clauses came before it.
SO_INCOMPLETE = ", so anything missing for them is not here."
# The button beside the sentence. Its own count, for the reason in the module
# docstring.
UNANSWERED_ONE = "1 artist unanswered"
UNANSWERED_SOME = "{count} artists unanswered"

# Not measured against the content the way the scan summary is. That dialog
# shows a report whose length is known once it is built; this one shows a list
# somebody scrolls, so a size that suits reading names is the useful answer
# and growing to fit thirty of them is not.
BODY_WIDTH_PX = 480
BODY_HEIGHT_PX = 420

DIALOG_TITLE = "Artists this run could not answer for"
INTRO = (
    "<p>A run asks two public catalogues about each artist whose genres you "
    "ticked. These questions ended without an answer, so nothing missing for "
    "these artists could be found. Everything else in the run is unaffected.</p>"
)
ASK_HEADING = "Could not be asked about"
ASK_WHY = (
    "<p>The catalogue returned an error for these. That is usually the service "
    "having a bad moment rather than anything about the artist, so running "
    "again later is worth a try.</p>"
)
RECOGNISED_HEADING = "Not recognised"
RECOGNISED_WHY = (
    "<p>The catalogue holds nobody under these names. A spelling that differs "
    "from the catalogue's reads this way, as does an artist it simply does not "
    "carry.</p>"
)
SEVERAL_HEADING = "Matched more than one artist"
SEVERAL_WHY = (
    "<p>Several artists share each of these names and nothing in the tags says "
    "which one is yours. Picking one would be guessing, so the run passed over "
    "them.</p>"
)


def counted(report: RunReport) -> int:
    """How many artists a run ended without an answer for."""
    return len(report.failed) + len(report.unresolved) + len(report.ambiguous)


def _clause(count: int, wording: tuple[str, str]) -> str:
    """One group's contribution to the sentence; empty where it is empty."""
    if not count:
        return ""
    return wording[0] if count == ONE else wording[1].format(count=count)


def _joined(clauses: list[str]) -> str:
    """The clauses as a list in English, with NO comma before the `and`."""
    if len(clauses) == ONE:
        return clauses[0]
    return f"{', '.join(clauses[:-1])} and {clauses[-1]}"


def sentence(report: RunReport) -> str:
    """The sentence owed where a run could not answer for every artist.

    Empty where every question was answered, so a run that went cleanly says
    exactly what it said before this existed rather than carrying a
    reassurance nobody needs.

    Opened with a capital by hand: a clause may begin with a digit, where
    capitalising is neither wanted nor possible, so the first character is
    lifted only when it is a letter.
    """
    clauses = [
        found
        for found in (
            _clause(len(report.failed), COULD_NOT_ASK),
            _clause(len(report.unresolved), NOT_RECOGNISED),
            _clause(len(report.ambiguous), MATCHED_SEVERAL),
        )
        if found
    ]
    if not clauses:
        return ""
    said = _joined(clauses)
    return f" {said[0].upper()}{said[1:]}{SO_INCOMPLETE}"


def button_label(report: RunReport) -> str:
    """What the button says, which has to stand up without its sentence."""
    total = counted(report)
    return UNANSWERED_ONE if total == ONE else UNANSWERED_SOME.format(count=total)


def _names(heading: str, why: str, names: tuple[str, ...]) -> str:
    """One group as a section; nothing at all where the group is empty."""
    if not names:
        return ""
    rows = "".join(f"<li>{escaped(name)}</li>" for name in names)
    return f"<h3>{heading}</h3>{why}<ul>{rows}</ul>"


def shortfall_html(report: RunReport) -> str:
    """The whole list, grouped by what went wrong rather than run in together.

    Grouped because the three are not the same news: one is worth trying
    again, one is a spelling to look at and one cannot be settled from a name
    at all. A single list of thirty names would hide that.

    The reasons the sources gave are deliberately left out. They are HTTP
    wording written for a program, they are already in the discovery file for
    anybody who wants them and a column of them beside the names would bury
    the names.
    """
    total = plural(counted(report), "artist", "artists")
    body = [
        f"<p><b>{total}</b> could not be answered for.</p>",
        INTRO,
        _names(
            ASK_HEADING,
            ASK_WHY,
            tuple(failure.artist for failure in report.failed),
        ),
        _names(RECOGNISED_HEADING, RECOGNISED_WHY, report.unresolved),
        _names(
            SEVERAL_HEADING,
            SEVERAL_WHY,
            tuple(each.artist for each in report.ambiguous),
        ),
    ]
    return "".join(body)


class ShortfallDialog(FirstStopDialog):
    """The names themselves, on the button beside the run's own sentence."""

    def __init__(self, report: RunReport, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(DIALOG_TITLE)
        layout = QVBoxLayout(self)
        body = QTextBrowser(self)
        body.setHtml(shortfall_html(report))
        layout.addWidget(body)
        layout.addLayout(close_row(self))
        # A list of names has no fixed length, so the pane is a tab stop
        # exactly when there is something below the fold. The house rule the
        # other reports already follow.
        self.pane = ReadingPane(body)
        self.resize(BODY_WIDTH_PX, BODY_HEIGHT_PX)


def build_shortfall_button(parent: QWidget) -> QPushButton:
    """The button, built hidden: a run that went cleanly shows nothing."""
    button = QPushButton("", parent)
    button.setFocusPolicy(Qt.FocusPolicy.TabFocus)
    button.hide()
    return button


class ShowingShortfall:
    """The button a run's shortfall is offered on; what opens it too.

    A mixin beside the words rather than more of `discovering`, which was
    at 395 lines with it: one concern, held where the sentence and the
    dialog it belongs to are already held.
    """

    def start_shortfall(self, button: QPushButton) -> None:
        """Take the button a run's shortfall is offered on.

        Handed in rather than built here, because where it goes is the
        window's business: the real one puts it in the status bar beside the
        sentence and pins it into the ring, while a window driven by a test
        needs it to exist and nothing more.
        """
        self._shortfall_button = button
        self._shortfall_report: RunReport | None = None
        button.clicked.connect(self.show_shortfall)

    def forget_shortfall(self) -> None:
        """Take the button away, which is what a run with nothing owed shows."""
        self._offer_shortfall(None)

    def _offer_shortfall(self, report: RunReport | None) -> None:
        """Offer the names of a run that could not answer for everybody.

        A report with nothing owed takes the button away exactly as None does,
        so a clean run leaves nothing behind for the last untidy one.
        """
        owed = report if report is not None and counted(report) else None
        self._shortfall_report = owed
        if owed is None:
            self._shortfall_button.hide()
            return
        self._shortfall_button.setText(button_label(owed))
        self._shortfall_button.show()

    def show_shortfall(self) -> None:
        """Open the names themselves, modally, over the window that ran it."""
        if self._shortfall_report is None:
            return
        dialog = ShortfallDialog(self._shortfall_report, parent=self)
        try:
            dialog.exec()
        finally:
            dialog.deleteLater()
