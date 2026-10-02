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

from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

from stellody.domain.showing import EVERYTHING, Showing
from stellody.ui.dialogs import FirstStopDialog
from stellody.ui.discovery_dialog import MIXES_LABEL
from stellody.ui.filter_controls import filter_controls, offer_apply
from stellody.ui.genre_folds import Folds
from stellody.ui.genre_grid import ASKING, GenreGrid
from stellody.ui.ringed_check import RingedCheckBox

TITLE = "Filter the answer"
FILTER_LABEL = "Filter"
# The row of kinds above the genres. FR-D86.
SHOW_HEADING = "Show:"
ALBUMS_LABEL = "Albums"
SHOW_SERIES_LABEL = "Series"
ARTISTS_LABEL = "Similar artists"


class ResultsFilterDialog(FirstStopDialog):
    """Collects which kinds and which of the run's genres to show."""

    def __init__(
        self,
        offered: tuple[str, ...] = (),
        picked: tuple[str, ...] = (),
        parent: QWidget | None = None,
        folds: Folds | None = None,
        showing: Showing = EVERYTHING,
    ) -> None:
        super().__init__(parent)
        self._offered = offered
        self.setWindowTitle(TITLE)
        outer = QVBoxLayout(self)
        # Kinds first, then genres: what sort of thing, then what it plays.
        row = QHBoxLayout()
        row.addWidget(QLabel(SHOW_HEADING, self))
        self.albums = self._kind(ALBUMS_LABEL, showing.albums, row)
        self.mixes = self._kind(MIXES_LABEL, showing.mixes, row)
        self.series = self._kind(SHOW_SERIES_LABEL, showing.series, row)
        self.artists = self._kind(ARTISTS_LABEL, showing.artists, row)
        row.addStretch()
        outer.addLayout(row)
        # Opened holding what is already picked, so a filter is adjusted
        # rather than rebuilt every time the chooser is opened.
        self.grid = GenreGrid("", self, manner=ASKING, folds=folds)
        self.grid.offer_only(offered)
        for name, box in self.grid.boxes.items():
            box.setChecked(name in offered and name in picked)
        outer.addWidget(self.grid)
        controls = filter_controls(self, FILTER_LABEL, self.clear)
        self.clear_button = controls.clear
        self.cancel_button = controls.cancel
        self.filter_button = controls.apply
        outer.addLayout(controls.row)
        offer_apply(
            self.filter_button,
            (*self.grid.boxes.values(), *self._kinds()),
            self._narrowing,
            filtering_already=self._narrowing(),
        )

    def _kind(self, label: str, ticked: bool, row: QHBoxLayout) -> RingedCheckBox:
        """One box of the "Show:" row."""
        box = RingedCheckBox(label, self)
        box.setChecked(ticked)
        row.addWidget(box)
        return box

    def _kinds(self) -> tuple[RingedCheckBox, ...]:
        """The four kind boxes, in the order drawn."""
        return (self.albums, self.mixes, self.series, self.artists)

    def _narrowing(self) -> bool:
        """Whether the boxes as they stand would hide anything."""
        return bool(self.picked()) or self.showing() != EVERYTHING

    def clear(self) -> None:
        """No filter at all: no genre ticked, every kind shown. FR-D86."""
        self.grid.set_all(False)
        for box in self._kinds():
            box.setChecked(True)

    def showing(self) -> Showing:
        """The kinds ticked. FR-D86."""
        return Showing(
            albums=self.albums.isChecked(),
            mixes=self.mixes.isChecked(),
            series=self.series.isChecked(),
            artists=self.artists.isChecked(),
        )

    def picked(self) -> tuple[str, ...]:
        """The genres ticked, in catalogue order; only ever ones on offer."""
        return tuple(name for name in self.grid.chosen() if name in self._offered)
