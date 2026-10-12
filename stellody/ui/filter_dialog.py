"""Asking the library for the albums of a genre, several at once.

The same catalogue the tag editor states with, asked rather than stated: see
`Manner` in `genre_grid`. Nothing here decides what survives; it collects a
question and hands it over as a `Narrowing`, which is pure and lives in the
domain.

**"Not stated" is a box of its own, apart from the catalogue.** It is not a
genre, so it does not sit among them: more than a tenth of the library carries
no genre tag at all and an album whose tag names nothing in the catalogue is in
the same position, since no tick could ever reach either. Without this box that
part of the library would be hidden behind a field nobody had filled in.

**Clearing is a button rather than a chore.** Undoing a filter by finding every
ticked box is the kind of tidying a dialog should do for somebody; the only alternative
on offer is closing the dialog and hunting.

**Years too, as Discover asks them** (Oliver's ruling, 2026-10-12): the same
two fields below the genres, narrowing to albums whose date tag falls inside
them. Typed years that cannot be used are said beneath the fields and take
Show away. FR-D99.

**The taste profiles are the Discover dialog's own** (Oliver's ruling,
2026-10-12): one list in one setting, so a profile saved or deleted in either
dialog is saved or deleted in both. Choosing one here ticks its genres and
puts its years back, since this dialog asks nothing about what to include;
the box apart from the catalogue is left as it was, being no genre. FR-D96.
Pressing Show with genres and years no profile holds offers to save them, as
Find does in Discover (Oliver's ruling, 2026-10-12). FR-D98.
"""

from __future__ import annotations

from PySide6.QtWidgets import QVBoxLayout, QWidget

from stellody.domain.narrowing import Narrowing
from stellody.domain.overrides import AlbumField
from stellody.domain.release_years import ANY_YEAR
from stellody.domain.taste import TasteProfile
from stellody.ui.dialogs import CONTROL_ICON_PX, FirstStopDialog
from stellody.ui.filter_controls import filter_controls, offer_apply
from stellody.ui.genre_folds import Folds
from stellody.ui.genre_grid import ASKING, GenreGrid
from stellody.ui.ringed_check import RingedCheckBox
from stellody.ui.taste_controls import TasteControls
from stellody.ui.taste_store import TasteStore
from stellody.ui.year_fields import YearsAsked, this_year

TITLE = "Filter by genre"
SHOW_LABEL = "Show"
UNSTATED_LABEL = "Albums that state no genre"
# The least the dialog is drawn at. The grid widens it past this rather than
# any box being clipped, should a category's open styles need more room.
DIALOG_WIDTH_PX = 700
# The gap that rules the box apart from the catalogue above it. Without it the
# box sits directly under the last column of genres and reads as one more of
# them, which is exactly what it is not.
APART_PX = 12


class FilterDialog(FirstStopDialog):
    """Collects the genres to narrow the library to; nothing else."""

    def __init__(
        self,
        asked: Narrowing | None = None,
        parent: QWidget | None = None,
        folds: Folds | None = None,
        taste: TasteStore | None = None,
        year_now: int | None = None,
    ) -> None:
        super().__init__(parent)
        asked = asked or Narrowing()
        self.setWindowTitle(TITLE)
        self.setMinimumWidth(DIALOG_WIDTH_PX)
        outer = QVBoxLayout(self)
        # Opened holding what is already being asked for, so a filter is
        # adjusted rather than rebuilt every time the dialog is opened.
        self.grid = GenreGrid("", self, manner=ASKING, folds=folds)
        for name in asked.wanted:
            self.grid.boxes[name].setChecked(True)
        outer.addWidget(self.grid)
        outer.addSpacing(APART_PX)
        self.unstated_box = RingedCheckBox(UNSTATED_LABEL, self)
        self.unstated_box.setChecked(asked.unstated)
        outer.addWidget(self.unstated_box)
        outer.addSpacing(APART_PX)
        # Opened holding the years already asked, as the boxes are. FR-D99.
        self.years = YearsAsked(
            asked.years, this_year() if year_now is None else year_now, self
        )
        outer.addWidget(self.years)
        # The same three controls the answer's chooser wears, with Taste
        # profiles beside Clear: see `filter_controls`.
        self.taste = TasteControls(self, taste, self._put_back, CONTROL_ICON_PX)
        controls = filter_controls(
            self, SHOW_LABEL, self.clear, extra=self.taste.button
        )
        self.clear_button = controls.clear
        self.cancel_button = controls.cancel
        self.show_button = controls.apply
        outer.addLayout(controls.row)
        refresh = offer_apply(
            self.show_button,
            (*self.grid.boxes.values(), self.unstated_box),
            lambda: not self.narrowing().is_open,
            filtering_already=not asked.is_open,
            refused=self.years.refused,
        )
        self.years.changed.connect(refresh)

    def accept(self) -> None:
        """Offer to keep genres and years no profile holds, then close. FR-D98.

        Guarded rather than merely disabled, as Find is in Discover: years
        that cannot be used never filter anything. FR-D99.
        """
        if self.years.refused():
            return
        self.taste.offer_filter(self.grid.chosen(), self.years.years())
        super().accept()

    def clear(self) -> None:
        """Untick everything and empty the years, leaving the dialog open.

        It does not close: clearing and then showing the whole library is two
        presses, while somebody who cleared by accident has lost nothing.
        """
        self.grid.set_all(False)
        self.unstated_box.setChecked(False)
        self.years.put(ANY_YEAR)

    def _put_back(self, profile: TasteProfile) -> None:
        """Tick exactly a taste profile's genres; put its years back. FR-D96."""
        self.grid.set_chosen(profile.genres)
        self.years.put(profile.years)

    def narrowing(self) -> Narrowing:
        """What has been asked for, as the domain takes it."""
        return Narrowing(
            field=AlbumField.GENRE,
            wanted=self.grid.chosen(),
            unstated=self.unstated_box.isChecked(),
            years=self.years.years(),
        )
