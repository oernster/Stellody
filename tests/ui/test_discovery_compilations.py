"""FR-D51 and FR-D52: including compilations, chosen and priced in the dialog."""

from __future__ import annotations

from discovery_wiring_support import make_window
from PySide6.QtWidgets import QWidget

from stellody.application.compilation_cost import Cost
from stellody.application.values import RunOutcome, RunReport
from stellody.domain.estimating import SECONDS_PER_MINUTE
from stellody.domain.genres import GENRES
from stellody.ui.discovery_dialog import (
    INCLUDE_COMPILATIONS_LABEL,
    NOTHING_NEW,
    DiscoveryDialog,
    cost_sentence,
)
from stellody.ui.discovery_worker import DiscoveryRunner

# Two genres ticked, for the cases that need the price to move.
FIRST, SECOND = GENRES[0], GENRES[1]


class Started:
    """A start that remembers what each run was handed."""

    def __init__(self) -> None:
        self.runs: list[tuple[tuple[str, ...], bool]] = []

    def __call__(self, genres: tuple[str, ...], compilations: bool) -> None:
        """Record the genres and whether compilations were included."""
        self.runs.append((genres, compilations))


def a_minute_a_genre(ticked: tuple[str, ...]) -> Cost:
    """One new name for every genre ticked, costing a minute each."""
    return Cost(names=len(ticked), seconds=len(ticked) * SECONDS_PER_MINUTE)


def test_compilations_start_left_out() -> None:
    """FR-D51: nothing slow happens unless somebody asks for it."""
    dialog = DiscoveryDialog()
    assert dialog.compilations.text() == INCLUDE_COMPILATIONS_LABEL
    assert not dialog.compilations.isChecked()


def test_the_run_is_told_whether_compilations_are_included() -> None:
    """The box is part of the question, handed over with the genres."""
    started = Started()
    dialog = DiscoveryDialog(start=started)
    dialog.grid.boxes[FIRST].setChecked(True)
    dialog.compilations.setChecked(True)
    dialog.find_button.click()
    assert started.runs == [((FIRST,), True)]


def test_the_box_is_a_stop_between_the_genres_and_the_buttons() -> None:
    """Read in the order it is written: what to look in, whether to widen, go."""
    dialog = DiscoveryDialog()
    chain: list[QWidget] = []
    widget = dialog.nextInFocusChain()
    while widget is not dialog and widget not in chain:
        chain.append(widget)
        widget = widget.nextInFocusChain()
    last_genre = max(chain.index(box) for box in dialog.grid.boxes.values())
    box = chain.index(dialog.compilations)
    assert last_genre < box < chain.index(dialog.select_button)


def test_the_cost_follows_the_ticks() -> None:
    """FR-D52: every tick changes who would be asked, so it changes the price."""
    dialog = DiscoveryDialog(cost=a_minute_a_genre)
    dialog.grid.boxes[FIRST].setChecked(True)
    assert dialog.cost_line.text() == cost_sentence(a_minute_a_genre((FIRST,)))
    dialog.grid.boxes[SECOND].setChecked(True)
    both = a_minute_a_genre((FIRST, SECOND))
    assert dialog.cost_line.text() == cost_sentence(both)


def test_nothing_new_to_ask_says_so() -> None:
    """A box that would add nothing says so rather than quoting nought minutes."""
    dialog = DiscoveryDialog(cost=lambda _ticked: Cost(names=0, seconds=0.0))
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


def test_the_choice_is_remembered_between_openings(application, monkeypatch) -> None:
    """FR-D51: it opens as it was last left."""
    window = make_window(application)
    seen: list[bool] = []

    def ticking(dialog: DiscoveryDialog) -> int:
        """Stand in for the modal wait: note the box, then tick it."""
        seen.append(dialog.compilations.isChecked())
        dialog.compilations.setChecked(True)
        return 0

    monkeypatch.setattr(DiscoveryDialog, "exec", ticking)
    window.open_discovery()
    window.open_discovery()
    assert seen == [False, True]


class Recording:
    """A service that notes whether it was asked to include compilations."""

    def __init__(self) -> None:
        self.included: list[bool] = []

    def run(self, albums, ticked, report, cancelled, compilations=False):
        """Note the choice, then end as a run that found nothing."""
        self.included.append(compilations)
        return RunReport(outcome=RunOutcome.COMPLETED)


def test_the_runner_hands_the_choice_to_the_run(application) -> None:
    """From the box to the service, through the thread in between."""
    service = Recording()
    runner = DiscoveryRunner()
    assert runner.start(service, (), ("Rock",), True)
    runner.wait()
    assert service.included == [True]
