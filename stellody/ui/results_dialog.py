"""What the last discovery run found, shown when the run ends.

Built from the discovery FILE rather than from the report still in hand when
a run finishes. One thing stays authoritative that way, so showing a past
run's answer again on some later day costs nothing beyond opening this on
what is already written down. FR-D28.

**Two kinds of artist, which mean opposite things.** A source artist is
somebody the library already holds who turns out to be missing records, so
those records are named under them. A candidate artist is somebody the library
holds nothing by, so every record they made is missing and naming them all
would mean a discography apiece. They are told apart by colour rather than by
wording. FR-D29, FR-D30, FR-D34.

**A candidate is asked about only when somebody opens it.** One catalogue
request costs at least the gap the terms ask for, so asking during the run
about every candidate that survived the genre filter would roughly double a
second stage that is already the longer half. It is paid one artist at a time,
by whoever wants the answer. FR-D31.

**It holds no catalogue and reaches no network.** Asking is handed in, so the
whole dialog can be driven with nothing behind it; where nothing is handed in,
a candidate simply does not open.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import (
    QHBoxLayout,
    QPushButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from stellody.domain.discovery import Gaps, ReleaseGroup, SimilarArtist
from stellody.ui.dialogs import FirstStopDialog, title_label
from stellody.ui.theme import Mode, palette_for

TITLE = "What the last run found"
CLOSE_LABEL = "Close"
# Said under a candidate whose lookup could not be made. Against that artist
# rather than in the status bar, since every other entry is still usable and
# a message elsewhere would say nothing about which one failed. FR-D32.
COULD_NOT_ASK = "Could not be looked up: {reason}"
# Said under a candidate the catalogue answered about with nothing worth
# offering. An entry that opens onto emptiness reads as one still loading.
NOTHING_OFFERED = "Nothing worth offering"
# Said under a candidate that arrived without an identifier, which is a name
# the similarity catalogue gave without saying who it meant. Nobody can be
# asked about that, so the entry says why rather than opening onto nothing.
NOBODY_TO_ASK = "The catalogue did not say which artist this is"
ASKING = "Asking the catalogue..."
# Wide enough for an album title under an artist under a heading without the
# titles wrapping; the same measurement the discovery dialog is built to.
DIALOG_WIDTH_PX = 700
DIALOG_HEIGHT_PX = 520
APART_PX = 12
# Where a candidate artist's identifier is kept, so an answer arriving later
# can find the rows it belongs under.
IDENTIFIER_ROLE = Qt.ItemDataRole.UserRole


def _coloured(item: QTreeWidgetItem, colour: str) -> QTreeWidgetItem:
    """Paint one row's writing, answering the row so this reads inline."""
    item.setForeground(0, QBrush(QColor(colour)))
    return item


class ResultsDialog(FirstStopDialog):
    """The run's answer: source artists with their albums, candidates to open.

    Non-modal by intention, which is the caller's business rather than this
    dialog's: a run takes minutes, so whatever somebody moved on to doing in
    the meantime is not something to interrupt. This simply does not insist.
    """

    def __init__(
        self,
        gaps: tuple[Gaps, ...] = (),
        asking: object | None = None,
        mode: Mode = Mode.DARK,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._asking = asking
        self._colour = palette_for(mode)
        # Every row a candidate artist occupies, by the identifier to ask
        # about. A list rather than one row, since two source artists can lead
        # to the same candidate and both rows are owed the same answer.
        self._rows: dict[str, list[QTreeWidgetItem]] = {}
        # The candidates already asked about, so opening one twice does not
        # ask twice and closing then reopening one shows what came back.
        self._answered: set[str] = set()
        self.setWindowTitle(TITLE)
        self.resize(DIALOG_WIDTH_PX, DIALOG_HEIGHT_PX)
        outer = QVBoxLayout(self)
        self.title = title_label(TITLE, self)
        outer.addWidget(self.title)
        outer.addSpacing(APART_PX)
        self.tree = self._built_tree(gaps)
        outer.addWidget(self.tree)
        outer.addLayout(self._buttons())
        self._listen()

    def _listen(self) -> None:
        """Take the answers the asker brings back, where there is one.

        Bound methods rather than lambdas, deliberately: the answers cross
        from a worker thread; a signal connected to a bare callable runs in
        the SENDER's thread, which is how a background thread comes to touch
        a widget.
        """
        if self._asking is None:
            return
        self._asking.ready.connect(self.show_releases)
        self._asking.failed.connect(self.show_failure)

    def _built_tree(self, gaps: tuple[Gaps, ...]) -> QTreeWidget:
        """The whole answer as a tree, source artists at the top level."""
        tree = QTreeWidget(self)
        tree.setHeaderHidden(True)
        tree.setColumnCount(1)
        for found in gaps:
            tree.addTopLevelItem(self._source_item(found))
        tree.expandToDepth(0)
        tree.itemExpanded.connect(self.opened)
        return tree

    def _source_item(self, found: Gaps) -> QTreeWidgetItem:
        """One source artist, with everything that artist turned up beneath.

        The albums first and the candidates after, which is the order they
        were found in: a record by somebody already held is a closer answer
        than an artist nobody has heard yet.
        """
        item = _coloured(QTreeWidgetItem([found.artist]), self._colour.source_artist)
        for album in found.albums:
            item.addChild(self._album_item(album))
        for candidate in found.artists:
            item.addChild(self._candidate_item(candidate))
        return item

    def _album_item(self, album: ReleaseGroup) -> QTreeWidgetItem:
        """One album the library does not hold."""
        return _coloured(QTreeWidgetItem([album.title]), self._colour.text)

    def _candidate_item(self, candidate: SimilarArtist) -> QTreeWidgetItem:
        """One artist the library holds nothing by, closed until it is opened.

        The arrow is stated rather than inherited from having children,
        because it has none: the whole point is that nothing is asked until
        somebody opens it. FR-D30.
        """
        item = _coloured(
            QTreeWidgetItem([candidate.name]), self._colour.candidate_artist
        )
        item.setData(0, IDENTIFIER_ROLE, candidate.identifier)
        item.setChildIndicatorPolicy(QTreeWidgetItem.ChildIndicatorPolicy.ShowIndicator)
        self._rows.setdefault(candidate.identifier, []).append(item)
        return item

    def _buttons(self) -> QHBoxLayout:
        """One way out, away to the right where the house puts it."""
        row = QHBoxLayout()
        row.addStretch()
        self.close_button = QPushButton(CLOSE_LABEL, self)
        self.close_button.setDefault(True)
        self.close_button.clicked.connect(self.reject)
        row.addWidget(self.close_button)
        return row

    def opened(self, item: QTreeWidgetItem) -> None:
        """Ask about a candidate artist the first time somebody opens it.

        A source artist opening is nothing to do: what it holds was found by
        the run. A candidate opened a second time is nothing to do either,
        since the answer to that question is already under it.
        """
        identifier = item.data(0, IDENTIFIER_ROLE)
        if identifier is None:
            return
        if not identifier:
            self._said_under(item, NOBODY_TO_ASK)
            return
        if identifier in self._answered or self._asking is None:
            return
        if self._asking.ask(identifier):
            self._answered.add(identifier)
            self._said_under(item, ASKING)

    def show_releases(self, identifier: str, releases: object) -> None:
        """Put what an artist released under every row that artist occupies."""
        for item in self._rows.get(identifier, ()):
            self._emptied(item)
            for album in releases:
                item.addChild(self._album_item(album))
            if not item.childCount():
                self._said_under(item, NOTHING_OFFERED)

    def show_failure(self, identifier: str, reason: str) -> None:
        """Say what went wrong against the artist it went wrong about.

        The rest of the answer is left exactly as it was: one artist nobody
        could look up is not a reason to lose a run that took minutes to
        make. Asked again the next time it is opened, since a service that
        refused once may well answer next time. FR-D32.
        """
        self._answered.discard(identifier)
        for item in self._rows.get(identifier, ()):
            self._said_under(item, COULD_NOT_ASK.format(reason=reason))

    def _said_under(self, item: QTreeWidgetItem, message: str) -> None:
        """Put one line under a row, replacing whatever was under it."""
        self._emptied(item)
        item.addChild(_coloured(QTreeWidgetItem([message]), self._colour.text_muted))

    @staticmethod
    def _emptied(item: QTreeWidgetItem) -> None:
        """Take everything out from under a row."""
        item.takeChildren()

    def reject(self) -> None:
        """Close, letting go of any question still in flight.

        A thread still running when Qt tears its owner down ends the process,
        so this waits rather than abandoning: a question is one request, where
        a run is minutes of them.

        The window's own close button arrives here too, since Qt routes a
        dialog's close through reject. That is why the tidying is here rather
        than in a `closeEvent` of its own.
        """
        self._let_go()
        super().reject()

    def _let_go(self) -> None:
        """Give up on every question still being asked."""
        if self._asking is not None:
            self._asking.stop()
