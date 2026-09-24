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
by whoever wants the answer. FR-D31. The asking itself is `results_asking`'s.

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

**The answer can be narrowed to some of the genres the run looked in.** A
whole-library answer ran to hundreds of pages. The Filter control at the foot
deals the pages again from what the picked genres leave; how is
`results_filtering`'s. FR-D54 to FR-D56.

**A strip at the top says when the catalogue is being asked.** One expansion
costs at least the gap the terms require and may wait out four refusals, so
several seconds of nothing happening is the ordinary case rather than a fault.
Reported the same day as looking stuck. The space is reserved rather than shown
only while something is in flight: a strip that appeared would push the whole
list down at the moment somebody clicked an arrow in it. At rest it carries the
instruction instead.
"""

from __future__ import annotations

import itertools

from PySide6.QtCore import QSize
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget

from stellody.application.shopping import Shopping
from stellody.domain.album import Album
from stellody.domain.discovery import Gaps, ReleaseGroup
from stellody.ui.dialogs import FirstStopDialog, title_label
from stellody.ui.results_asking import AskingResults
from stellody.ui.results_filtering import FilteringResults
from stellody.ui.results_foot import COPIED, COPY_LABEL, foot_row
from stellody.ui.results_pager import ResultsPager
from stellody.ui.results_pages import ResultsPages
from stellody.ui.results_room import (
    DIALOG_HEIGHT_PX,
    DIALOG_WIDTH_PX,
    opening_size,
)
from stellody.ui.results_ticks import anything_ticked, ticked_albums
from stellody.ui.results_top import ResultsTop
from stellody.ui.shops_dialog import ShopsDialog
from stellody.ui.theme import Mode, palette_for

# One name for the window and for the heading inside it, so the taskbar, the
# title bar and the screen itself cannot come to say different things.
#
# It read "What the last run found" until 2026-09-09, when Oliver asked what
# run that meant. Stellody has two: a scan of the library and a discovery over
# the catalogues. The heading names which, since a screen somebody opened
# minutes after asking for it has to say what it is an answer to.
TITLE = "What the last discovery run found"
APART_PX = 12


class ResultsDialog(AskingResults, FilteringResults, FirstStopDialog):
    """The run's answer: source artists with their albums, candidates to open.

    Whether it is modal is the caller's business rather than this dialog's:
    the window opens it with `exec`, so it is modal, as FR-D28 states. Nothing
    here insists either way.
    """

    def __init__(
        self,
        gaps: tuple[Gaps, ...] = (),
        asking: object | None = None,
        shopping: Shopping | None = None,
        mode: Mode = Mode.DARK,
        ticked: tuple[str, ...] = (),
        library: tuple[Album, ...] = (),
        remembered: dict[str, tuple[str, ...]] | None = None,
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
        # What each of them answered, kept for the rows a filter deals.
        self._released: dict[str, tuple[ReleaseGroup, ...]] = {}
        self._start_filtering(gaps, ticked, library, remembered)
        self.setWindowTitle(TITLE)
        self.setMinimumSize(DIALOG_WIDTH_PX, DIALOG_HEIGHT_PX)
        # Held, since a filter deals its pages into the same room.
        self._room = self._opening_size()
        self.resize(self._room)
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
        self.top = ResultsTop(self._colour, ticked, self)
        self.key = self.top.key
        self.asking_bar = self.top.bar
        outer.addWidget(self.top)
        # The pages and the note of where every candidate landed arrive
        # together, since one is only useful with the other. How many columns
        # and how long a page follow the room the dialog just took, so the
        # answer is spread over the room there is rather than over numbers
        # somebody guessed.
        self.pages = ResultsPages(gaps, self._colour, self._room, self)
        self._take_pages()
        outer.addWidget(self.pages)
        self.pager = ResultsPager(len(self.pages.pages), self)
        self.pager.turned.connect(self.turn_to)
        # The pager goes INTO the row of controls rather than above it. Ruled
        # by Oliver on 2026-09-09, looking at the shipped screen: two stacked
        # rows under the answer put the way through the answer on one line and
        # the way out of it on another, which reads as two separate feet. One
        # row, immediately under the answer.
        outer.addLayout(self._buttons())
        self._state_ring()
        self._offer_filter()
        self._listen()
        self._ticks_changed()

    def _opening_size(self) -> QSize:
        """How big this opens on the screen it is opening on.

        The screen is asked for rather than assumed, so the same request means
        the same share of a laptop panel and of a wide monitor. Where there is
        no screen to ask, which is what an offscreen test has, the floor is
        the answer: a dialog that cannot measure a screen must still open.

        What is done with the room is `results_room`'s, so the share, the
        floor and the 13 inch ceiling can be read at widths no machine running
        the suite has.
        """
        screen = self.screen() or QGuiApplication.primaryScreen()
        if screen is None:
            return QSize(DIALOG_WIDTH_PX, DIALOG_HEIGHT_PX)
        return opening_size(screen.availableGeometry().size())

    def _take_pages(self) -> None:
        """Read the rows off the pages just dealt; listen to their lists.

        Called when the dialog is built and again whenever a filter deals the
        answer afresh, so the two cannot come to wire the lists differently.
        """
        self._rows = self.pages.rows
        self.sources = self.pages.sources
        for tree in self.pages.trees:
            tree.itemExpanded.connect(self.opened)
            tree.itemChanged.connect(self.ticks_changed)

    def first_stop(self) -> QWidget | None:
        """The first list on the page showing; the base's answer without one.

        Ruled by Oliver on 2026-09-17: the dialog opens on the answer. The base
        passes over every scroll area so a reading dialog does not open on its
        page, which a list also is to Qt, so the list is named here instead.
        """
        showing = [tree for tree in self.pages.trees if tree.isVisibleTo(self)]
        return showing[0] if showing else super().first_stop()

    def _state_ring(self) -> None:
        """Tab walks the lists left to right, then the controls as drawn.

        Stated rather than left to the order the widgets were made in, which
        walked the controls out of drawn order: measured on 2026-09-17 by
        taking this out and reading the Tab tests fail. It is not stated again
        when a filter deals the answer afresh: the new lists join the chain
        after Close, which is where the cycle already wants them, measured the
        same way. A list on a page not showing is hidden, so Tab passes it by.
        """
        stops = (
            *self.pages.trees,
            self.filter_button,
            self.copy_button,
            self.shops_button,
            self.pager.previous_button,
            self.pager.next_button,
            self.close_button,
        )
        for earlier, later in itertools.pairwise(stops):
            QWidget.setTabOrder(earlier, later)

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

    def _buttons(self) -> QHBoxLayout:
        """The one row under the answer, built in `results_foot.py`."""
        row, filter_button, copy_button, shops_button, close_button = foot_row(
            self,
            self.pager,
            self.open_filter,
            self.copy_ticked,
            self.open_shops,
            self.reject,
        )
        self.filter_button = filter_button
        self.copy_button = copy_button
        self.shops_button = shops_button
        self.close_button = close_button
        return row

    def turn_to(self, at: int) -> None:
        """Show this page; say from there what can be done next.

        The pager is told rather than left to work it out, so the words and
        the picture always describe the page actually in front: the two would
        otherwise be two accounts of where somebody is.
        """
        self.pages.show_page(at)
        self.pager.showing(self.pages.showing)

    def ticks_changed(self, _item=None, _column: int = 0) -> None:
        """Qt hands a row and a column; what changed does not matter here."""
        self._ticks_changed()

    def _ticks_changed(self) -> None:
        """Nothing ticked is nothing to look up, so both controls go.

        The same rule the discovery dialog applies to its own Find button: a
        press that can only report emptiness is a press worth preventing.
        FR-S04.
        """
        ready = self._shopping is not None and anything_ticked(self.pages.trees)
        self.copy_button.setEnabled(ready)
        self.shops_button.setEnabled(ready)
        self.copy_button.setText(COPY_LABEL)
        if self.shops is not None:
            self.shops.follow(self.ticked())

    def ticked(self) -> tuple:
        """The albums ticked on screen, in the order they are drawn.

        On screen only: a tick a filter is holding back is kept for when the
        filter clears, never sent anywhere while out of sight. FR-D56.
        """
        return ticked_albums(self.pages.trees)

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

        One shops dialog, brought back on every press rather than made again.
        Closing it only hides it, so a new one per press left every earlier
        one standing, each still holding the albums ticked when it opened.
        FR-S44.
        """
        if self._shopping is None:
            return
        if self.shops is None:
            self.shops = ShopsDialog(self._shopping, self.ticked(), self._mode, self)
        else:
            self.shops.follow(self.ticked())
        self.shops.show()
        self.shops.raise_()
        self.shops.activateWindow()

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
