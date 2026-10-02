"""FR-D51, FR-D52, FR-D85: what else a run takes in, chosen and priced."""

from __future__ import annotations

from discovery_wiring_support import make_window
from PySide6.QtWidgets import QApplication, QWidget

from stellody.application.compilation_cost import Cost
from stellody.application.values import RunOutcome, RunReport
from stellody.domain.estimating import SECONDS_PER_MINUTE
from stellody.domain.genres import GENRES
from stellody.domain.including import OWN_ALBUMS, WIDEST, Including
from stellody.ui.discovery_choices import widened_by
from stellody.ui.discovery_dialog import (
    CREDITS_LABEL,
    MIXES_LABEL,
    NOTHING_NEW,
    SERIES_LABEL,
    DiscoveryDialog,
    cost_sentence,
)
from stellody.ui.discovery_worker import DiscoveryRunner
from stellody.ui.settings_keys import SETTING_DISCOVER_COMPILATIONS, TRUE

# Two genres ticked, for the cases that need the price to move.
FIRST, SECOND = GENRES[0], GENRES[1]


class Started:
    """A start that remembers what each run was handed."""

    def __init__(self) -> None:
        self.runs: list[tuple[tuple[str, ...], Including]] = []

    def __call__(
        self, genres: tuple[str, ...], including: Including, years: object = None
    ) -> None:
        """Record the genres and what else was taken in."""
        self.runs.append((genres, including))


def a_minute_a_genre(ticked: tuple[str, ...], including: Including) -> Cost:
    """One new name for every genre ticked, costing a minute each."""
    return Cost(names=len(ticked), seconds=len(ticked) * SECONDS_PER_MINUTE)


def boxes(dialog: DiscoveryDialog) -> list:
    """The three boxes, in the order they are drawn."""
    return [dialog.credits, dialog.series, dialog.mixes]


def test_three_boxes_start_as_a_run_that_widens_to_nothing() -> None:
    """FR-D51: nothing slow happens unless asked for; FR-D80: mixes offered."""
    dialog = DiscoveryDialog()
    assert [box.text() for box in boxes(dialog)] == [
        CREDITS_LABEL,
        SERIES_LABEL,
        MIXES_LABEL,
    ]
    assert dialog.including() == OWN_ALBUMS


def test_the_run_is_told_what_else_to_take_in() -> None:
    """The boxes are part of the question, handed over with the genres."""
    started = Started()
    dialog = DiscoveryDialog(start=started)
    dialog.grid.boxes[FIRST].setChecked(True)
    dialog.series.setChecked(True)
    dialog.mixes.setChecked(False)
    dialog.find_button.click()
    assert started.runs == [((FIRST,), Including(series=True, mixes=False))]


def test_the_boxes_sit_between_the_genres_and_the_buttons() -> None:
    """Read in the order written: what to look in, what to take in, go."""
    dialog = DiscoveryDialog()
    chain: list[QWidget] = []
    widget = dialog.nextInFocusChain()
    while widget is not dialog and widget not in chain:
        chain.append(widget)
        widget = widget.nextInFocusChain()
    last_genre = max(chain.index(box) for box in dialog.grid.boxes.values())
    placed = [chain.index(box) for box in boxes(dialog)]
    assert last_genre < placed[0] < placed[1] < placed[2]
    assert placed[2] < chain.index(dialog.select_button)


def test_the_cost_follows_the_ticks() -> None:
    """FR-D52: every tick changes who would be asked, so it changes the price."""
    dialog = DiscoveryDialog(cost=a_minute_a_genre, including=WIDEST)
    dialog.grid.boxes[FIRST].setChecked(True)
    assert dialog.cost_line.text() == cost_sentence(a_minute_a_genre((FIRST,), WIDEST))
    dialog.grid.boxes[SECOND].setChecked(True)
    both = a_minute_a_genre((FIRST, SECOND), WIDEST)
    assert dialog.cost_line.text() == cost_sentence(both)


def test_the_price_is_asked_for_the_boxes_ticked() -> None:
    """FR-D85: the price is of what the boxes take in, so it is handed them."""
    asked: list[Including] = []

    def noting(ticked: tuple[str, ...], including: Including) -> Cost:
        asked.append(including)
        return Cost(names=1, seconds=SECONDS_PER_MINUTE)

    dialog = DiscoveryDialog(cost=noting, including=Including(credits=True))
    dialog.grid.boxes[FIRST].setChecked(True)
    dialog.series.setChecked(True)
    assert asked[-1] == Including(credits=True, series=True)


def test_nothing_costly_ticked_says_nothing() -> None:
    """DJ mixes cost no request, so with neither costly box there is no price."""
    dialog = DiscoveryDialog(cost=a_minute_a_genre)
    dialog.grid.boxes[FIRST].setChecked(True)
    assert dialog.cost_line.text() == ""


def test_nothing_new_to_ask_says_so() -> None:
    """A box that would add nothing says so rather than quoting nought minutes."""
    dialog = DiscoveryDialog(
        cost=lambda _ticked, _including: Cost(names=0, seconds=0.0),
        including=WIDEST,
    )
    dialog.grid.boxes[FIRST].setChecked(True)
    assert dialog.cost_line.text() == NOTHING_NEW


def test_a_dialog_given_no_price_says_nothing_about_one() -> None:
    """A window with no memory to price from shows no line rather than a guess."""
    dialog = DiscoveryDialog()
    assert dialog.cost_line.isHidden()


def test_the_sentence_names_one_artist_and_a_short_wait_plainly() -> None:
    """No "1 artists", no "0 minutes"."""
    one = cost_sentence(Cost(names=1, seconds=SECONDS_PER_MINUTE / 2))
    many = cost_sentence(Cost(names=314, seconds=314 * 2.2))
    assert "1 artists" not in one
    assert "0 minutes" not in one
    assert "314 artists" in many


def test_the_sentence_names_the_series_too() -> None:
    """A series is not an artist, so it is counted in its own words."""
    both = cost_sentence(Cost(names=3, seconds=SECONDS_PER_MINUTE * 2, series=2))
    alone = cost_sentence(Cost(names=0, seconds=SECONDS_PER_MINUTE / 2, series=1))
    assert both.startswith(
        "3 artists and 2 series on compilations in these genres have not"
    )
    assert alone.startswith("One series on compilations in these genres has not")


def test_the_choices_are_remembered_between_openings(application, monkeypatch) -> None:
    """FR-D51, FR-D85: the boxes open as they were last left."""
    window = make_window(application)
    seen: list[Including] = []

    def ticking(dialog: DiscoveryDialog) -> int:
        """Stand in for the modal wait: note the boxes, then move them."""
        seen.append(dialog.including())
        dialog.credits.setChecked(True)
        dialog.mixes.setChecked(False)
        return 0

    monkeypatch.setattr(DiscoveryDialog, "exec", ticking)
    window.open_discovery()
    window.open_discovery()
    assert seen == [OWN_ALBUMS, Including(credits=True, mixes=False)]


def test_the_old_box_answers_for_the_two_it_split_into(
    application, monkeypatch
) -> None:
    """A listener who ticked the one box finds both of its halves ticked."""
    window = make_window(application)
    window._settings.set_setting(SETTING_DISCOVER_COMPILATIONS, TRUE)
    seen: list[Including] = []
    monkeypatch.setattr(
        DiscoveryDialog, "exec", lambda dialog: seen.append(dialog.including()) or 0
    )
    window.open_discovery()
    assert seen == [WIDEST]


class Recording:
    """A service that notes what it was asked to take in."""

    def __init__(self) -> None:
        self.included: list[Including] = []

    def run(self, albums, ticked, report, cancelled, including=OWN_ALBUMS, years=None):
        """Note the choices, then end as a run that found nothing."""
        self.included.append(including)
        return RunReport(outcome=RunOutcome.COMPLETED)


def test_the_runner_hands_the_choices_to_the_run(application) -> None:
    """From the boxes to the service, through the thread in between."""
    service = Recording()
    runner = DiscoveryRunner()
    assert runner.start(service, (), ("Rock",), WIDEST)
    runner.wait()
    assert service.included == [WIDEST]


def test_the_diary_says_what_a_run_took_in() -> None:
    """Written down so a run can be placed against what it was asked."""
    assert widened_by(OWN_ALBUMS) == ""
    assert widened_by(Including(series=True, mixes=False)) == (
        "; with other volumes of series, no DJ mixes"
    )


def test_select_all_prices_once_rather_than_once_a_box() -> None:
    """Measured on 2026-10-02: 57 prices froze the dialog for 4.1 seconds."""
    asked: list[tuple[str, ...]] = []

    def counting(ticked: tuple[str, ...], including: Including) -> Cost:
        asked.append(ticked)
        return Cost(names=1, seconds=SECONDS_PER_MINUTE)

    dialog = DiscoveryDialog(cost=counting, including=WIDEST)
    asked.clear()
    dialog.select_button.click()
    assert len(asked) == 1
    assert asked[0] == dialog.chosen()
    assert QApplication.overrideCursor() is None
