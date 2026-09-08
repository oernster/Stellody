"""The run's answer dealt across several lists side by side.

One tall list was what a run answered in until 2026-09-08, when Oliver showed
a two genre run already running off the foot of a screen with the room to
show it sitting empty either side. A whole library answers with hundreds of
source artists, so the shape of the answer is a column of text nobody reaches
the end of.

**Several trees rather than one tree of several columns.** A tree's own
columns hold facets of one row, which is not what this is: these are separate
runs of rows read top to bottom, the way a sleeve's back is read. It is the
same choice the album pane makes for an album's tracks, for the same reason.

**One selection across the lot.** Clicking in the second column clears the
first, so the highlight is somewhere in the answer rather than once per
column. What a press ACTS on is the ticks rather than the selection, so this
is about what somebody reads rather than about what a control does.

**The trees know nothing about being dealt.** Which artist landed where is
`results_room`'s arithmetic; building a tree of them is `results_tree`'s. This
puts the two together and is the only place that knows both.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QTreeWidget, QTreeWidgetItem, QWidget

from stellody.domain.discovery import Gaps
from stellody.ui.results_room import columns_for, dealt_into_columns
from stellody.ui.results_tree import CandidateRows, filled_tree
from stellody.ui.theme import Palette

# The gap between one column and the next, which is what the dialog puts
# between its own parts. Enough that two lists read as two rather than as one
# list with a rule down it.
COLUMN_GAP_PX = 12


class ResultsColumns(QWidget):
    """Every source artist the run found, spread over the room available."""

    def __init__(
        self,
        gaps: tuple[Gaps, ...],
        colour: Palette,
        width: int,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        # A container is never a stop on the keyboard ring; the lists in it
        # are. It paints nothing either, so there is no border to lose.
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        # Every candidate artist's rows, filled by all the columns together:
        # the same candidate can sit under two source artists that were dealt
        # into different columns; both rows are owed the same answer.
        self.rows: CandidateRows = {}
        self.trees: tuple[QTreeWidget, ...] = ()
        self._settling = False
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(COLUMN_GAP_PX)
        landed: list[QTreeWidgetItem | None] = [None] * len(gaps)
        trees = []
        for column in self._columns(gaps, width):
            tree = filled_tree(
                tuple(gaps[at] for at in column), colour, self.rows, self
            )
            for place, at in enumerate(column):
                landed[at] = tree.topLevelItem(place)
            tree.itemSelectionChanged.connect(self._one_selection)
            trees.append(tree)
            row.addWidget(tree, 1)
        self.trees = tuple(trees)
        # The source artists in the order the run answered in rather than in
        # the order they were dealt, so a reader can still say what the first
        # one was without knowing where it landed.
        self.sources = tuple(landed)

    @staticmethod
    def _columns(gaps: tuple[Gaps, ...], width: int) -> tuple[tuple[int, ...], ...]:
        """Which artists go in which column, with no empty column built.

        Fewer artists than the room affords means fewer columns; an empty
        column would be a stop on the keyboard ring holding nothing. A run
        that found nobody still gets one, since a screen saying nothing must
        still be a screen.
        """
        dealt = dealt_into_columns(gaps, columns_for(width))
        return tuple(column for column in dealt if column) or ((),)

    def _one_selection(self) -> None:
        """Clear every other column, so one highlight stands in the answer.

        Clearing a column asks it to say its selection changed, which arrives
        back here; the flag is what stops the first press from walking round
        the columns for ever.
        """
        if self._settling:
            return
        self._settling = True
        for tree in self.trees:
            if tree is not self.sender():
                tree.clearSelection()
        self._settling = False
