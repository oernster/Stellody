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

**Years too, as Discover asks them** (Oliver's ruling, 2026-10-12): the same
two fields below the genres, showing only the albums released inside them.
Similar artists have no year, so the years leave them be, as a run does.
FR-D99.

**Taste profiles too, beside Clear** (Oliver's ruling, 2026-10-12): the same
list as Discover and the library's filter, read from the one setting. A
profile ticks those of its genres the run looked in and puts its years back;
the other genres could only filter to nothing, so they are passed over, as a
genre not on offer always is. The kinds are left as they stand, being no
genre. FR-D96. Pressing Filter with genres and years no profile holds offers
to save them (Oliver's ruling, 2026-10-12). FR-D98.
"""

from __future__ import annotations

from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

from stellody.domain.release_years import ANY_YEAR, ReleaseYears
from stellody.domain.showing import EVERYTHING, Showing
from stellody.domain.taste import TasteProfile
from stellody.ui.dialogs import CONTROL_ICON_PX, FirstStopDialog
from stellody.ui.discovery_dialog import MIXES_LABEL
from stellody.ui.filter_controls import filter_controls, offer_apply
from stellody.ui.genre_folds import Folds
from stellody.ui.genre_grid import ASKING, GenreGrid
from stellody.ui.ringed_check import RingedCheckBox
from stellody.ui.taste_controls import TasteControls
from stellody.ui.taste_store import TasteStore
from stellody.ui.year_fields import YearsAsked, this_year

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
        taste: TasteStore | None = None,
        years: ReleaseYears = ANY_YEAR,
        year_now: int | None = None,
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
        # Opened holding the years already asked, as the boxes are. FR-D99.
        self.years = YearsAsked(
            years, this_year() if year_now is None else year_now, self
        )
        outer.addWidget(self.years)
        self.taste = TasteControls(self, taste, self._put_back, CONTROL_ICON_PX)
        controls = filter_controls(
            self, FILTER_LABEL, self.clear, extra=self.taste.button
        )
        self.clear_button = controls.clear
        self.cancel_button = controls.cancel
        self.filter_button = controls.apply
        outer.addLayout(controls.row)
        refresh = offer_apply(
            self.filter_button,
            (*self.grid.boxes.values(), *self._kinds()),
            self._narrowing,
            filtering_already=self._narrowing(),
            refused=self.years.refused,
        )
        self.years.changed.connect(refresh)

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
        """Whether the boxes and years as they stand would hide anything."""
        return (
            bool(self.picked())
            or self.showing() != EVERYTHING
            or self.years.years().is_bounded
        )

    def accept(self) -> None:
        """Offer to keep genres and years no profile holds, then close. FR-D98.

        Guarded rather than merely disabled: years that cannot be used never
        filter anything. FR-D99.
        """
        if self.years.refused():
            return
        self.taste.offer_filter(self.picked(), self.years.years())
        super().accept()

    def clear(self) -> None:
        """No filter at all: no genre ticked, every kind shown, any year."""
        self.grid.set_all(False)
        for box in self._kinds():
            box.setChecked(True)
        self.years.put(ANY_YEAR)

    def _put_back(self, profile: TasteProfile) -> None:
        """Tick exactly a taste profile's genres the run looked in; put its
        years back. FR-D96."""
        offered = set(self._offered)
        self.grid.set_chosen(tuple(g for g in profile.genres if g in offered))
        self.years.put(profile.years)

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
