"""Narrowing the results to some of the genres the run looked in.

Its own module rather than more of `results_dialog.py`: filtering is a concern
with a clean edge, being everything between a press of the Filter control and
the pages dealt again from what it leaves. Which artists it leaves is the
domain's rule, `filtered_answer`; this puts that rule on screen. FR-D54 to
FR-D56.

**A filter deals the pages again.** Pages are dealt by height, so hiding rows
inside pages dealt for the whole answer would leave columns half empty under a
pager counting pages of nothing. The pages are built afresh from what is shown
instead, by the same arithmetic a run's whole answer is dealt by.

**A tick outlives the rows it was made on.** Dealing again throws the rows
away, so the ticks are read off first and put back after. A tick on an album
the filter withholds is kept rather than dropped. Ruled by Oliver on
2026-09-13: a tick is somebody's decision while a filter is only where they
are looking. Copy and Find in shops still read the rows on screen, so nothing
out of sight is ever sent anywhere.

**Nothing to judge by leaves the control there and disabled.** A dialog given
no library, no memory of what candidates play or a run naming no genres has
nothing a filter could decide with.
"""

from __future__ import annotations

from PySide6.QtCore import QSize
from PySide6.QtWidgets import QDialog, QPushButton, QTreeWidgetItem

from stellody.domain.album import Album
from stellody.domain.discovery import Gaps, filtered_answer
from stellody.domain.shopping import WantedAlbum
from stellody.ui.results_filter import ResultsFilterDialog
from stellody.ui.results_pages import ResultsPages
from stellody.ui.results_ticks import (
    ARTIST_ROLE,
    TICKED,
    every_row_across,
    is_tickable,
)
from stellody.ui.theme import Palette


def _album_on(row: QTreeWidgetItem) -> WantedAlbum:
    """The album a tickable row stands for."""
    return WantedAlbum(artist=row.data(0, ARTIST_ROLE), title=row.text(0))


class FilteringResults:
    """The Filter control's half of the results dialog.

    A mixin over the dialog, which builds the pages, the pager and the foot
    this reaches for.
    """

    filter_button: QPushButton
    pages: ResultsPages
    _colour: Palette
    _room: QSize

    def _start_filtering(
        self,
        gaps: tuple[Gaps, ...],
        looked_in: tuple[str, ...],
        library: tuple[Album, ...],
        remembered: dict[str, tuple[str, ...]] | None,
    ) -> None:
        """Hold what a filter judges by. Not remembered between openings."""
        self._gaps = gaps
        self._looked_in = looked_in
        self._library = library
        self._remembered = remembered
        self._picked: tuple[str, ...] = ()
        # Every album ticked on any rows dealt so far, including rows the
        # filter is holding back right now.
        self._kept: set[WantedAlbum] = set()

    def _offer_filter(self) -> None:
        """Enable the control only where there is something to judge by."""
        self.filter_button.setEnabled(
            bool(self._library)
            and self._remembered is not None
            and bool(self._looked_in)
        )

    def filter_dialog(self) -> ResultsFilterDialog:
        """The chooser, offering the run's genres and holding what is picked."""
        return ResultsFilterDialog(self._looked_in, self._picked, self)

    def open_filter(self) -> None:
        """Ask which genres to show; show them.

        The control is checkable, so Qt has already pressed it down or let it
        up by the time this runs. What it shows is settled here once the
        chooser closes, since a cancelled press changed nothing.
        """
        chooser = self.filter_dialog()
        try:
            if chooser.exec() == QDialog.DialogCode.Accepted:
                self.filter_to(chooser.picked())
        finally:
            self.filter_button.setChecked(bool(self._picked))
            chooser.deleteLater()

    def filter_to(self, picked: tuple[str, ...]) -> None:
        """Show the answer as these genres leave it; nothing picked is all."""
        self._picked = picked
        shown = filtered_answer(
            self._gaps, self._library, self._remembered or {}, picked
        )
        self._deal(shown.gaps)
        self.top.say_withheld(shown.unjudged)
        self.filter_button.setChecked(bool(picked))

    def _deal(self, gaps: tuple[Gaps, ...]) -> None:
        """Build the pages again from these gaps, in the place the old ones held."""
        self._keep_ticks()
        dealt = ResultsPages(gaps, self._colour, self._room, self)
        self.layout().replaceWidget(self.pages, dealt)
        self.pages.hide()
        self.pages.deleteLater()
        self.pages = dealt
        self._take_pages()
        self._replay_releases()
        self._put_ticks_back()
        self.pager.set_pages(len(dealt.pages))
        self.turn_to(0)
        self._ticks_changed()

    def _keep_ticks(self) -> None:
        """Add what is ticked on screen; drop what is shown unticked.

        Ticked wins where one album is both, which two rows under one
        candidate opened twice can make it.
        """
        ticked: set[WantedAlbum] = set()
        unticked: set[WantedAlbum] = set()
        for row in every_row_across(self.pages.trees):
            if not is_tickable(row):
                continue
            if row.checkState(0) is TICKED:
                ticked.add(_album_on(row))
            else:
                unticked.add(_album_on(row))
        self._kept = (self._kept - unticked) | ticked

    def _put_ticks_back(self) -> None:
        """Tick every row just dealt whose album was ticked before."""
        for row in every_row_across(self.pages.trees):
            if is_tickable(row) and _album_on(row) in self._kept:
                row.setCheckState(0, TICKED)
