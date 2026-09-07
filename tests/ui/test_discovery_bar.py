"""The bar in the tray that a discovery run reports to.

Its whole reason for existing is that the second half of a run used to report
nothing, so a bar that had stopped moving was indistinguishable from a hang.
What is asserted here is that it moves in both halves, that it says which half
it is in and that it never becomes a control.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget

from stellody.application.values import DiscoveryProgress, DiscoveryStage
from stellody.ui.discovery_progress import RESTING, DiscoveryBar
from stellody.ui.tray_metrics import BUTTON_PX


def make_bar() -> tuple[DiscoveryBar, QWidget]:
    """A bar with nothing behind it; the holder is returned to keep it alive."""
    holder = QWidget()
    return DiscoveryBar(holder, BUTTON_PX), holder


def test_at_rest_it_says_what_the_space_is_for(application) -> None:
    """Reserved rather than hidden, so the tray never moves under anybody."""
    bar, _holder = make_bar()
    assert bar.format() == RESTING
    assert bar.value() == 0


def test_it_is_never_a_stop_on_the_ring(application) -> None:
    """A report is not a control, so the keyboard steps over it."""
    bar, _holder = make_bar()
    assert bar.focusPolicy() == Qt.FocusPolicy.NoFocus


def test_it_reserves_its_place_whatever_it_is_saying(application) -> None:
    """The width cannot follow the text, else the tray moves as it reports."""
    bar, _holder = make_bar()
    resting = bar.width()
    bar.show_progress(
        DiscoveryProgress(artist="Jools Holland & His Rhythm & Blues", done=1, total=4)
    )
    assert bar.width() == resting


def test_it_draws_how_far_through_the_stage_the_run_is(application) -> None:
    """Counted in work finished, which is what a bar is answering."""
    bar, _holder = make_bar()
    bar.show_progress(DiscoveryProgress(artist="Muddy Waters", done=1, total=4))
    assert bar.value() == 25


def test_it_names_the_stage_rather_than_the_artist(application) -> None:
    """No strip of a toolbar holds "Jools Holland & His Rhythm & Blues
    Orchestra", so the name goes where there is room for it."""
    bar, _holder = make_bar()
    long_name = "Jools Holland & His Rhythm & Blues Orchestra"
    bar.show_progress(DiscoveryProgress(artist=long_name, done=3, total=4))
    assert "Looking up" in bar.format()
    assert long_name not in bar.format()
    assert long_name in bar.toolTip()
    assert "4 of 4" in bar.toolTip()


def test_the_second_half_of_a_run_says_that_it_is_the_second_half(
    application,
) -> None:
    """The half that used to report nothing at all is named as its own."""
    bar, _holder = make_bar()
    bar.show_progress(
        DiscoveryProgress(
            artist="Robert Cray", done=6, total=31, stage=DiscoveryStage.NARROWING
        )
    )
    assert "Checking styles" in bar.format()
    assert "Robert Cray" in bar.toolTip()
    assert "7 of 31" in bar.toolTip()


def test_an_ended_run_puts_it_back_to_resting(application) -> None:
    """However a run ended, the space goes back to naming itself."""
    bar, _holder = make_bar()
    bar.show_progress(DiscoveryProgress(artist="Howlin' Wolf", done=2, total=4))
    bar.rest()
    assert bar.format() == RESTING
    assert bar.value() == 0
