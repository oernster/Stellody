"""Asking what the library is missing, in the genres somebody chose.

The same catalogue the filter asks with, for the same reason: two grids built
from one catalogue cannot come to disagree, while a second vocabulary invented
here would.

**Ticking is what scopes the run, so it is what the dialog is mostly made of.**
A run over the whole library names 327 artists to two public catalogues; a run
over Folk names one. The ticks are the difference between those, which is why
the action cannot be pressed until at least one box is.

**It asks, then it leaves.** Ruled on 2026-09-07. A run takes minutes at the
rate the catalogues permit; a dialog held open for all of them is one
somebody has to work around to carry on listening. Pressing Find hands the
ticks over and closes; the run reports to the bar in the tray and the button
that started it becomes the one that stops it. So this dialog knows nothing
about a run: it cannot report on one, cannot cancel one and does not know
whether one is under way.

**It holds no service and reaches no network.** Starting is handed in, so the
whole dialog can be driven with nothing behind it.
"""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from stellody.shared import resources
from stellody.ui.dialogs import CLOSE_ICON, FirstStopDialog, title_label, wearing
from stellody.ui.genre_grid import ASKING, GenreGrid

TITLE = "Discover new music"
FIND_LABEL = "Find"
CLOSE_LABEL = "Close"
# What the dialog says before anything has been asked of it. It names where the
# answer will appear, since the dialog will not be there to show it.
RESTING = (
    "Tick the genres to find similar music in, then press Find. "
    "This closes; the toolbar reports on the search."
)
# Wide enough for the catalogue's three columns without the longest name
# wrapping; the same measurement the filter dialog is built to.
DIALOG_WIDTH_PX = 700
APART_PX = 12


class DiscoveryDialog(FirstStopDialog):
    """Collects the genres to search in, then hands them over and closes."""

    def __init__(
        self,
        start: Callable[[tuple[str, ...]], None] = lambda _genres: None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._start = start
        self.setWindowTitle(TITLE)
        self.setMinimumWidth(DIALOG_WIDTH_PX)
        outer = QVBoxLayout(self)
        # The same words as the title bar, from the same constant: two spellings
        # of one name is the kind of drift nobody notices until it is shipped.
        self.title = title_label(TITLE, self)
        outer.addWidget(self.title)
        outer.addSpacing(APART_PX)
        self.grid = GenreGrid("", self, manner=ASKING)
        for box in self.grid.boxes.values():
            box.toggled.connect(self._ticks_changed)
        outer.addWidget(self.grid)
        outer.addSpacing(APART_PX)
        self.message = QLabel(RESTING, self)
        self.message.setWordWrap(True)
        outer.addWidget(self.message)
        outer.addLayout(self._buttons())
        self._ticks_changed()

    def _buttons(self) -> QHBoxLayout:
        """Away to the left, then the one that does the work."""
        row = QHBoxLayout()
        row.addStretch()
        self.close_button = wearing(
            QPushButton(CLOSE_LABEL, self), resources.find_asset(CLOSE_ICON)
        )
        self.close_button.clicked.connect(self.reject)
        row.addWidget(self.close_button)
        # The same picture the control that opens this dialog wears, since a
        # press here is the thing that button promised.
        self.find_button = wearing(
            QPushButton(FIND_LABEL, self), resources.discover_icon_path()
        )
        self.find_button.setDefault(True)
        self.find_button.clicked.connect(self._find)
        row.addWidget(self.find_button)
        return row

    def chosen(self) -> tuple[str, ...]:
        """The genres ticked, in catalogue order."""
        return self.grid.chosen()

    def _ticks_changed(self) -> None:
        """Nothing ticked is nothing to ask about, so the action goes.

        A run over no genres has no artists to look up, so offering it invites
        a press that can only report emptiness.
        """
        self.find_button.setEnabled(bool(self.chosen()))

    def _find(self) -> None:
        """Hand the ticked genres over, then get out of the way.

        Guarded rather than merely disabled: the action is reachable from the
        keyboard while it is off, so a run over nothing could otherwise ask two
        public catalogues about nobody.
        """
        if not self.chosen():
            return
        self._start(self.chosen())
        self.accept()
