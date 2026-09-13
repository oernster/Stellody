"""Choosing which of a run's genres to narrow its answer to.

The library's own filter offers the whole catalogue, since a library can hold
anything. A run's answer holds only what the run looked in, so a genre it
never looked in could only ever filter to nothing: that box is hidden rather
than offered. Ruled by Oliver on 2026-09-13. FR-D54.

**Hidden rather than built to a shorter list.** The grid always builds the
whole catalogue; hiding what is not on offer keeps one grid with one set of
rules about how a genre is ticked, where a second grid built from a list of
its own would be a second place for those rules to live.
"""

from __future__ import annotations

from PySide6.QtWidgets import QHBoxLayout, QPushButton, QVBoxLayout, QWidget

from stellody.ui.dialogs import FirstStopDialog
from stellody.ui.genre_grid import ASKING, GenreGrid

TITLE = "Filter the answer by genre"
CLEAR_LABEL = "Clear"
CANCEL_LABEL = "Cancel"
FILTER_LABEL = "Filter"


class ResultsFilterDialog(FirstStopDialog):
    """Collects which of the run's genres to show; nothing else."""

    def __init__(
        self,
        offered: tuple[str, ...] = (),
        picked: tuple[str, ...] = (),
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._offered = offered
        self.setWindowTitle(TITLE)
        outer = QVBoxLayout(self)
        # Opened holding what is already picked, so a filter is adjusted
        # rather than rebuilt every time the chooser is opened.
        self.grid = GenreGrid("", self, manner=ASKING)
        for name, box in self.grid.boxes.items():
            if name not in offered:
                box.hide()
            box.setChecked(name in offered and name in picked)
        outer.addWidget(self.grid)
        outer.addLayout(self._buttons())

    def _buttons(self) -> QHBoxLayout:
        """Clear away to the left, then out or on with it."""
        row = QHBoxLayout()
        self.clear_button = QPushButton(CLEAR_LABEL, self)
        self.clear_button.clicked.connect(self.clear)
        row.addWidget(self.clear_button)
        row.addStretch()
        self.cancel_button = QPushButton(CANCEL_LABEL, self)
        self.cancel_button.clicked.connect(self.reject)
        row.addWidget(self.cancel_button)
        self.filter_button = QPushButton(FILTER_LABEL, self)
        self.filter_button.setDefault(True)
        self.filter_button.clicked.connect(self.accept)
        row.addWidget(self.filter_button)
        return row

    def clear(self) -> None:
        """Untick everything, leaving the chooser open to be asked again."""
        self.grid.set_all(False)

    def picked(self) -> tuple[str, ...]:
        """The genres ticked, in catalogue order; only ever ones on offer."""
        return tuple(name for name in self.grid.chosen() if name in self._offered)
