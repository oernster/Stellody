"""FR-D58, FR-D59, FR-D63, FR-D64: the years, from the dialog to the results."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QTreeWidget, QWidget

from stellody.application.values import (
    PERCENT,
    DiscoveryProgress,
    DiscoveryStage,
    RunOutcome,
    RunReport,
)
from stellody.domain.discovery import ReleaseGroup
from stellody.domain.genres import GENRES
from stellody.domain.release_years import (
    ANY_YEAR,
    FIRST_YEAR,
    Bound,
    ReleaseYears,
    YearFault,
)
from stellody.domain.shopping import WantedAlbum
from stellody.ui.discovery_dialog import RESTING, DiscoveryDialog
from stellody.ui.discovery_progress import STAGE_NAMES, DiscoveryBars
from stellody.ui.discovery_worker import DiscoveryRunner
from stellody.ui.results_ticks import TICKED, ticked_albums
from stellody.ui.results_tree import album_item
from stellody.ui.results_words import album_row, looked_in
from stellody.ui.theme import Mode, palette_for
from stellody.ui.tray_metrics import BUTTON_PX
from stellody.ui.year_fields import ANY_YEAR_HINT, FAULTS, FIELD_NAMES

GENRE = GENRES[0]
THIS_YEAR = 2026
EIGHTIES = ReleaseYears(1980, 1989)


class Started:
    """A start that remembers the years each run was handed."""

    def __init__(self) -> None:
        self.years: list[ReleaseYears] = []

    def __call__(
        self, genres: tuple[str, ...], including: object, years: ReleaseYears
    ) -> None:
        """Record the years."""
        self.years.append(years)


def ready(started: Started | None = None) -> DiscoveryDialog:
    """A dialog standing in 2026 with one genre ticked."""
    dialog = DiscoveryDialog(start=started or Started(), this_year=THIS_YEAR)
    dialog.grid.boxes[GENRE].setChecked(True)
    return dialog


def typed(dialog: DiscoveryDialog, earliest: str, latest: str) -> None:
    """Type these into the two fields."""
    dialog.years.earliest.setText(earliest)
    dialog.years.latest.setText(latest)


class TestTheFields:
    def test_both_open_empty_saying_any_year(self) -> None:
        dialog = ready()
        for field in (dialog.years.earliest, dialog.years.latest):
            assert field.text() == ""
            assert field.placeholderText() == ANY_YEAR_HINT

    def test_left_empty_the_run_is_asked_for_every_year(self) -> None:
        started = Started()
        dialog = ready(started)
        dialog.find_button.click()
        assert started.years == [ANY_YEAR]

    def test_the_years_typed_are_handed_over(self) -> None:
        started = Started()
        dialog = ready(started)
        typed(dialog, "1980", "1989")
        dialog.find_button.click()
        assert started.years == [EIGHTIES]

    def test_one_year_alone_is_handed_over_alone(self) -> None:
        started = Started()
        dialog = ready(started)
        typed(dialog, "", "1979")
        dialog.find_button.click()
        assert started.years == [ReleaseYears(latest=1979)]


class TestRefusing:
    def test_a_reversed_range_is_said_and_find_goes(self) -> None:
        dialog = ready()
        typed(dialog, "1990", "1980")
        assert dialog.message.text() == FAULTS[YearFault.REVERSED]
        assert not dialog.find_button.isEnabled()

    def test_not_a_year_names_the_field(self) -> None:
        dialog = ready()
        typed(dialog, "", "198")
        said = dialog.message.text()
        assert said.startswith(FIELD_NAMES[Bound.LATEST])
        assert "not a year" in said

    def test_the_ceiling_follows_the_year_the_dialog_stands_in(self) -> None:
        dialog = ready()
        typed(dialog, "", str(THIS_YEAR + 1))
        assert dialog.find_button.isEnabled()
        typed(dialog, "", str(THIS_YEAR + 2))
        assert not dialog.find_button.isEnabled()
        assert str(THIS_YEAR + 1) in dialog.message.text()

    def test_the_floor_is_said_with_its_year(self) -> None:
        dialog = ready()
        typed(dialog, str(FIRST_YEAR - 1), "")
        assert str(FIRST_YEAR) in dialog.message.text()

    def test_putting_it_right_brings_find_back(self) -> None:
        dialog = ready()
        typed(dialog, "1990", "1980")
        typed(dialog, "1980", "1990")
        assert dialog.message.text() == RESTING
        assert dialog.find_button.isEnabled()

    def test_a_refused_range_is_never_run_even_when_pressed(self) -> None:
        """Guarded, not merely disabled: the keyboard can reach it."""
        started = Started()
        dialog = ready(started)
        typed(dialog, "1990", "1980")
        dialog._find()
        assert started.years == []

    def test_nothing_ticked_still_takes_find_away(self) -> None:
        dialog = DiscoveryDialog(this_year=THIS_YEAR)
        typed(dialog, "1980", "1989")
        assert not dialog.find_button.isEnabled()


class TestTheKeyboard:
    def test_the_fields_come_after_the_box_and_before_the_buttons(self) -> None:
        dialog = ready()
        chain: list[QWidget] = []
        widget = dialog.nextInFocusChain()
        while widget is not dialog and widget not in chain:
            chain.append(widget)
            widget = widget.nextInFocusChain()
        box = chain.index(dialog.mixes)
        earliest = chain.index(dialog.years.earliest)
        latest = chain.index(dialog.years.latest)
        assert box < earliest < latest < chain.index(dialog.select_button)

    def test_the_row_holding_them_takes_no_focus(self) -> None:
        assert ready().years.focusPolicy() == Qt.FocusPolicy.NoFocus


class TestTheBars:
    def test_checking_years_is_drawn_on_the_styles_bar(self) -> None:
        holder = QWidget()
        bars = DiscoveryBars(holder, BUTTON_PX)
        bars.show_progress(DiscoveryProgress(artist="Dilby", done=0, total=2))
        bars.show_progress(
            DiscoveryProgress(
                artist="New Voice", done=0, total=2, stage=DiscoveryStage.DATING
            )
        )
        assert bars.looking_up.value() == PERCENT
        assert bars.checking_styles.label == STAGE_NAMES[DiscoveryStage.DATING]
        assert bars.checking_styles.wanted.startswith(bars.checking_styles.label)

    def test_at_rest_the_styles_bar_is_the_styles_again(self) -> None:
        holder = QWidget()
        bars = DiscoveryBars(holder, BUTTON_PX)
        bars.show_progress(
            DiscoveryProgress(artist="x", done=0, total=1, stage=DiscoveryStage.DATING)
        )
        bars.rest()
        assert bars.checking_styles.label == STAGE_NAMES[DiscoveryStage.NARROWING]
        assert bars.resting


class TestTheResultsSayTheYears:
    def test_a_closed_range(self) -> None:
        assert looked_in(("Rock",), EIGHTIES) == (
            "Looked in 1 genre: Rock; released 1980 to 1989"
        )

    def test_one_bound_alone(self) -> None:
        assert looked_in(("Rock",), ReleaseYears(earliest=2020)).endswith(
            "; released 2020 or later"
        )
        assert looked_in(("Rock",), ReleaseYears(latest=1979)).endswith(
            "; released 1979 or earlier"
        )

    def test_no_years_says_nothing_more(self) -> None:
        assert looked_in(("Rock",)) == "Looked in 1 genre: Rock"


class TestAnAlbumRowSaysItsYear:
    """FR-D68: the year beside the title, never inside what a shop is sent."""

    def test_the_year_follows_the_title(self) -> None:
        assert album_row("Tripwires", 2019) == "Tripwires (2019)"

    def test_no_year_adds_nothing(self) -> None:
        assert album_row("Demos", None) == "Demos"

    def test_a_shop_is_asked_for_the_title_alone(self) -> None:
        tree = QTreeWidget()
        row = album_item(
            ReleaseGroup(title="Tripwires", released="2019-02-01"),
            "Lane 8",
            palette_for(Mode.DARK),
        )
        tree.addTopLevelItem(row)
        row.setCheckState(0, TICKED)
        assert row.text(0) == "Tripwires (2019)"
        assert ticked_albums((tree,)) == (
            WantedAlbum(artist="Lane 8", title="Tripwires"),
        )


class Recording:
    """A service that notes the years it was asked for."""

    def __init__(self) -> None:
        self.years: list[ReleaseYears] = []

    def run(self, albums, ticked, report, cancelled, including=None, years=None):
        """Note the years, then end as a run that found nothing."""
        self.years.append(years)
        return RunReport(outcome=RunOutcome.COMPLETED)


def test_the_runner_hands_the_years_to_the_run(application) -> None:
    """From the dialog's answer to the service, through the thread between."""
    service = Recording()
    runner = DiscoveryRunner()
    assert runner.start(service, (), ("Rock",), False, EIGHTIES)
    runner.wait()
    assert service.years == [EIGHTIES]
