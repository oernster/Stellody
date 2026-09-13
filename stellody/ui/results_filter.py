"""Choosing which of a run's genres to narrow its answer to.

The library's own filter offers the whole catalogue, since a library can hold
anything. A run's answer holds only what the run looked in, so a genre it
never looked in could only ever filter to nothing: that box is hidden rather
than offered. Ruled by Oliver on 2026-09-13. FR-D54.

**Hidden rather than built to a shorter list.** The grid always builds the
whole catalogue; hiding what is not on offer keeps one grid with one set of
rules about how a genre is ticked, where a second grid built from a list of
its own would be a second place for those rules to live.

Its three controls are the library filter's, pictures and all: see
`filter_controls`.
"""

from __future__ import annotations

from PySide6.QtWidgets import QVBoxLayout, QWidget

from stellody.ui.dialogs import FirstStopDialog
from stellody.ui.filter_controls import filter_controls
from stellody.ui.genre_grid import ASKING, GenreGrid

TITLE = "Filter the answer by genre"
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
        controls = filter_controls(self, FILTER_LABEL, self.clear)
        self.clear_button = controls.clear
        self.cancel_button = controls.cancel
        self.filter_button = controls.apply
        outer.addLayout(controls.row)

    def clear(self) -> None:
        """Untick everything, leaving the chooser open to be asked again."""
        self.grid.set_all(False)

    def picked(self) -> tuple[str, ...]:
        """The genres ticked, in catalogue order; only ever ones on offer."""
        return tuple(name for name in self.grid.chosen() if name in self._offered)
