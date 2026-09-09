"""The run's answer a page at a time, with every page already built.

A run over two genres already ran off the foot of the screen, which is what
dealt the answer into columns on 2026-09-08. A run over a whole library
answers with hundreds of source artists, so three columns of it are three
lists nobody reaches the end of: the scrollbar says how much is left and
nothing says where you are in it.

**A page fills every one of its columns.** How deep a column is filled comes
from the height of the dialog exactly as the number of columns comes from its
width, so a laptop panel gets a shorter page rather than the same page with
more in it. A column holding an artist taller than the screen scrolls, which
is one artist's worth of scrolling rather than the library's: measured from
Oliver's own library, an artist runs from 1 row to 109 against a column of 30,
so a page that refused to overflow a column could not be filled at all and
drew one column where it should have drawn three. The arithmetic is
`results_room`'s; this puts the pages on screen.

**Every page is built at once and kept.** Building the page somebody turns to
would be the obvious economy and it would be the wrong one: a tick is held by
the row it is on, so a page rebuilt on the way back would lose whatever was
ticked on it, where an album ticked on the first page is exactly what the shop
controls beneath are for. Nothing here is fetched either way, since a page
holds what the run already answered. Only opening a candidate asks anything;
what comes back is written to every row that candidate occupies, whichever
page it is on.

**A page nobody is looking at is not on the keyboard ring.** Qt leaves a
hidden widget out of the focus chain, so Tab walks the page in front rather
than every list in the answer.
"""

from __future__ import annotations

from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import QStackedWidget, QTreeWidget, QVBoxLayout, QWidget

from stellody.domain.discovery import Gaps
from stellody.ui.results_columns import ResultsColumns
from stellody.ui.results_room import columns_for, paged, rows_for
from stellody.ui.results_tree import CandidateRows
from stellody.ui.theme import Palette


class ResultsPages(QWidget):
    """Every source artist the run found, dealt across pages of columns."""

    def __init__(
        self,
        gaps: tuple[Gaps, ...],
        colour: Palette,
        room: QSize,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        # A container is never a stop on the keyboard ring; the lists in it
        # are. It paints nothing either, so there is no border to lose.
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.rows: CandidateRows = {}
        held = QVBoxLayout(self)
        held.setContentsMargins(0, 0, 0, 0)
        self._stack = QStackedWidget(self)
        self._stack.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        held.addWidget(self._stack)
        self.pages = tuple(
            ResultsColumns(page, colour, room.width(), self._stack, self.rows)
            for page in paged(gaps, columns_for(room.width()), rows_for(room.height()))
        )
        for page in self.pages:
            self._stack.addWidget(page)
        # Both flattened across the pages, since what reads them is asking
        # about the ANSWER rather than about what is on screen: what is ticked
        # goes to a shop wherever it was ticked; the first source artist is
        # the first the run answered with, whichever page it landed on.
        self.trees: tuple[QTreeWidget, ...] = tuple(
            tree for page in self.pages for tree in page.trees
        )
        self.sources = tuple(item for page in self.pages for item in page.sources)

    @property
    def showing(self) -> int:
        """Which page is in front, counting from nothing."""
        return self._stack.currentIndex()

    def show_page(self, at: int) -> None:
        """Turn to this page, where there is one; do nothing where there is not.

        Guarded rather than trusted, since what asks for a page is a control
        that can be reached from the keyboard while it is off.
        """
        if 0 <= at < len(self.pages):
            self._stack.setCurrentIndex(at)
