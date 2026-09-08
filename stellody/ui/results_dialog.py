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

**It says what it is showing, in a key and on every row.** Reported on
2026-09-07: shown a tree of blue names, amber names and plain names, Oliver
asked which lines were albums and which were tracks, then whether two of the
amber names were artists at all. An amber row indented under a blue one reads
as an album under an artist; its own children then read as tracks. So the kind
is now written on the row rather than carried by the colour alone, with a key
at the top saying which colour is which. The words are in
`results_words.py`; this module is where they are put on screen.

**An album can be ticked; what is ticked can be taken to a shop.** Stage
two, specified in SHOPS.md. A tick box is a state that survives focus moving
and a row being rebuilt, which a selection does not; the two controls beneath
the list act on whatever is ticked. Nothing here opens anything: the use case
handed in does that, over ports, so this whole dialog still runs with no
browser and no shop file.

**A strip at the top says when the catalogue is being asked.** One expansion
costs at least the gap the terms require and may wait out two refusals, so
several seconds of nothing happening is the ordinary case rather than a fault.
Reported the same day as looking stuck. The space is reserved rather than shown
only while something is in flight: a strip that appeared would push the whole
list down at the moment somebody clicked an arrow in it. At rest it carries the
instruction instead.
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QHBoxLayout,
    QPushButton,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from stellody.application.shopping import Shopping
from stellody.domain.discovery import Gaps
from stellody.shared import resources
from stellody.ui.dialogs import FirstStopDialog, title_label
from stellody.ui.icons import plain_icon
from stellody.ui.results_ticks import anything_ticked, ticked_albums
from stellody.ui.results_top import ResultsTop
from stellody.ui.results_tree import (
    IDENTIFIER_ROLE,
    NAME_ROLE,
    album_item,
    built_tree,
    coloured,
)
from stellody.ui.results_words import (
    COULD_NOT_ASK,
    NOBODY_TO_ASK,
    NOTHING_OFFERED,
    candidate_row,
)
from stellody.ui.shops_dialog import ShopsDialog
from stellody.ui.theme import Mode, palette_for

TITLE = "What the last run found"
CLOSE_LABEL = "Close"
# Wide enough for an album title under an artist under a heading without the
# titles wrapping; the same measurement the discovery dialog is built to.
DIALOG_WIDTH_PX = 700
DIALOG_HEIGHT_PX = 560
APART_PX = 12
COPY_LABEL = "Copy"
SHOPS_LABEL = "Find in shops"
# Said on the copy control once it has been pressed, so a press that changed
# nothing visible is still a press somebody saw work.
COPIED = "Copied"
# What the two controls carry. The shop artwork is Oliver's; the copy artwork
# is the two squares everything else in the world uses for it. A control whose
# artwork is missing keeps its words rather than becoming a blank square.
SHOP_ICON = "shop.png"
COPY_ICON = "copy.png"


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
        shopping: Shopping | None = None,
        mode: Mode = Mode.DARK,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._asking = asking
        # A dialog given none offers neither control, the same shape as a
        # window with no cover chooser: there and disabled rather than absent.
        self._shopping = shopping
        # The shops dialog, once there is one. Named here rather than only
        # where it is built, since an attribute that exists only after a
        # press is one that raises for anybody asking whether it is open.
        self.shops: ShopsDialog | None = None
        self._mode = mode
        self._colour = palette_for(mode)
        # The candidates already asked about, so opening one twice does not
        # ask twice and closing then reopening one shows what came back.
        self._answered: set[str] = set()
        self.setWindowTitle(TITLE)
        self.resize(DIALOG_WIDTH_PX, DIALOG_HEIGHT_PX)
        # Who is being asked about right now, by identifier. What the strip
        # at the top reads; also why it can say a name rather than a number
        # when there is only one.
        self._in_flight: dict[str, str] = {}
        outer = QVBoxLayout(self)
        self.title = title_label(TITLE, self)
        outer.addWidget(self.title)
        outer.addSpacing(APART_PX)
        # The key and the busy strip together, since both explain the screen
        # rather than acting on it. Named here as well so what reads them does
        # not have to know which widget they ended up in.
        self.top = ResultsTop(self._colour, self)
        self.key = self.top.key
        self.asking_bar = self.top.bar
        outer.addWidget(self.top)
        # The tree and the note of where every candidate landed arrive
        # together, since one is only useful with the other.
        self.tree, self._rows = built_tree(gaps, self._colour, self)
        self.tree.itemExpanded.connect(self.opened)
        self.tree.itemChanged.connect(self.ticks_changed)
        outer.addWidget(self.tree)
        outer.addLayout(self._buttons())
        self._listen()
        self._ticks_changed()

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

    def _say_what_is_being_asked(self) -> None:
        """Put whoever is being looked up on the strip above the list."""
        self.top.say_asking(tuple(self._in_flight.values()))

    def _buttons(self) -> QHBoxLayout:
        """What can be done with the ticked albums, then the way out."""
        row = QHBoxLayout()
        self.copy_button = self._control(COPY_LABEL, COPY_ICON, self.copy_ticked)
        row.addWidget(self.copy_button)
        self.shops_button = self._control(SHOPS_LABEL, SHOP_ICON, self.open_shops)
        row.addWidget(self.shops_button)
        row.addStretch()
        self.close_button = QPushButton(CLOSE_LABEL, self)
        self.close_button.setDefault(True)
        self.close_button.clicked.connect(self.reject)
        row.addWidget(self.close_button)
        return row

    def _control(self, label: str, artwork: str, pressed) -> QPushButton:
        """One control acting on the ticked albums, wearing its artwork.

        The words stay whatever the artwork does, since a picture-only button
        here would be two unlabelled squares under a list; the artwork is what
        makes them findable rather than what says what they do.
        """
        button = QPushButton(label, self)
        found = resources.find_asset(artwork)
        if found is not None:
            button.setIcon(plain_icon(found))
        button.setAutoDefault(False)
        button.clicked.connect(pressed)
        return button

    def ticks_changed(self, _item=None, _column: int = 0) -> None:
        """Qt hands a row and a column; what changed does not matter here."""
        self._ticks_changed()

    def _ticks_changed(self) -> None:
        """Nothing ticked is nothing to look up, so both controls go.

        The same rule the discovery dialog applies to its own Find button: a
        press that can only report emptiness is a press worth preventing.
        FR-S04.
        """
        ready = self._shopping is not None and anything_ticked(self.tree)
        self.copy_button.setEnabled(ready)
        self.shops_button.setEnabled(ready)
        self.copy_button.setText(COPY_LABEL)

    def ticked(self) -> tuple:
        """The albums somebody has ticked, in the order they are drawn."""
        return ticked_albums(self.tree)

    def copy_ticked(self) -> None:
        """Put the ticked albums on the clipboard as text. FR-S14."""
        if self._shopping is None:
            return
        self._shopping.copy(self.ticked())
        self.copy_button.setText(COPIED)

    def open_shops(self) -> None:
        """Offer the shops for whatever is ticked. FR-S05.

        Held on the dialog rather than left as a local, since a dialog nobody
        keeps a name for goes away with the call that made it.
        """
        if self._shopping is None:
            return
        self.shops = ShopsDialog(self._shopping, self.ticked(), self._mode, self)
        self.shops.show()

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
            self._in_flight[identifier] = item.data(0, NAME_ROLE)
            self._say_what_is_being_asked()

    def show_releases(self, identifier: str, releases: object) -> None:
        """Put what an artist released under every row that artist occupies.

        The row itself gains the count, which answers how many lines sit
        beneath it; the key above answers what they are.
        """
        albums = tuple(releases)
        self._in_flight.pop(identifier, None)
        self._say_what_is_being_asked()
        for item in self._rows.get(identifier, ()):
            self._emptied(item)
            name = item.data(0, NAME_ROLE)
            item.setText(0, candidate_row(name, len(albums)))
            for album in albums:
                item.addChild(album_item(album, name, self._colour))
            if not albums:
                self._said_under(item, NOTHING_OFFERED)

    def show_failure(self, identifier: str, reason: str) -> None:
        """Say what went wrong against the artist it went wrong about.

        The rest of the answer is left exactly as it was: one artist nobody
        could look up is not a reason to lose a run that took minutes to
        make. Asked again the next time it is opened, since a service that
        refused once may well answer next time. FR-D32.
        """
        self._answered.discard(identifier)
        self._in_flight.pop(identifier, None)
        self._say_what_is_being_asked()
        for item in self._rows.get(identifier, ()):
            self._said_under(item, COULD_NOT_ASK.format(reason=reason))

    def _said_under(self, item: QTreeWidgetItem, message: str) -> None:
        """Put one line under a row, replacing whatever was under it."""
        self._emptied(item)
        item.addChild(coloured(QTreeWidgetItem([message]), self._colour.text_muted))

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
