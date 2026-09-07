"""What the tray does while a discovery run is under way.

Split from the endings suite beside it when that module reached the line cap.
The seam is the one the feature already has: what is SAID about a run that has
ended against what is SHOWN while one is still going.
"""

from __future__ import annotations

import pytest
from discovery_wiring_support import (
    RunnerInProgress,
    a_report,
    answer,
    make_window,
)
from PySide6.QtWidgets import QMessageBox

from stellody.application.values import DiscoveryProgress
from stellody.ui.discovering import STOP_QUESTION_EARLY
from stellody.ui.discovery_progress import STOPPING
from stellody.ui.tray_metrics import STOP_DISCOVERY_TOOLTIP


def test_a_started_run_turns_the_button_into_a_stop(application) -> None:
    """One control carries both meanings once the dialog has gone."""
    window = make_window(application)
    window.begin_discovery(("Rock",))
    try:
        assert window._tray.discover_button.toolTip() == STOP_DISCOVERY_TOOLTIP
    finally:
        window._discovery_runner.wait()


def test_pressing_it_during_a_run_stops_the_run(
    application, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The whole reason the button changes meaning rather than going dead."""
    window = make_window(application)
    runner = RunnerInProgress()
    window._discovery_runner = runner
    answer(monkeypatch, QMessageBox.StandardButton.Yes)
    window.open_discovery()
    assert runner.stopped == 1, "it cancelled rather than opening a second dialog"


def test_stopping_is_asked_about_before_it_happens(
    application, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A run is minutes of waiting and none of it survives being stopped."""
    window = make_window(application)
    runner = RunnerInProgress()
    window._discovery_runner = runner
    answer(monkeypatch, QMessageBox.StandardButton.No)
    window.open_discovery()
    assert runner.stopped == 0, "the run was left alone"
    assert window._tray.discovery_bar.format() != STOPPING


def test_the_question_names_how_much_would_be_thrown_away(
    application, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Named before it happens rather than reported after it."""
    asked: list[str] = []
    window = make_window(application)
    window._discovery_runner = RunnerInProgress()
    window.discovery_progressed(
        DiscoveryProgress(artist="Muddy Waters", done=7, total=31)
    )
    answer(monkeypatch, QMessageBox.StandardButton.No, asked)
    window.open_discovery()
    assert "7 of 31" in asked[0]


def test_the_question_still_asks_before_anything_has_been_reported(
    application, monkeypatch: pytest.MonkeyPatch
) -> None:
    """There is no count yet, which is not a reason to skip the asking."""
    asked: list[str] = []
    window = make_window(application)
    window._discovery_runner = RunnerInProgress()
    answer(monkeypatch, QMessageBox.StandardButton.No, asked)
    window.open_discovery()
    assert asked == [STOP_QUESTION_EARLY]


def test_an_ended_run_forgets_where_it_had_got_to(
    application, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Else the next run's question quotes the last run's counts."""
    asked: list[str] = []
    window = make_window(application)
    window.discovery_progressed(
        DiscoveryProgress(artist="Muddy Waters", done=7, total=31)
    )
    window.discovery_completed(a_report(albums=0, artists=0))
    window._discovery_runner = RunnerInProgress()
    answer(monkeypatch, QMessageBox.StandardButton.No, asked)
    window.open_discovery()
    assert asked == [STOP_QUESTION_EARLY]


def test_a_stop_is_acknowledged_before_the_run_has_stopped(
    application, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A run gives up between requests, so the press lands before the ending."""
    window = make_window(application)
    runner = RunnerInProgress()
    window._discovery_runner = runner
    answer(monkeypatch, QMessageBox.StandardButton.Yes)
    window.discovery_progressed(
        DiscoveryProgress(artist="Muddy Waters", done=1, total=4)
    )
    window.open_discovery()
    assert window._tray.discovery_bar.format() == STOPPING
    assert runner.stopped == 1


def test_progress_reported_after_a_stop_does_not_undo_the_stopping(
    application, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Reported as the stop not working, on 2026-09-07.

    The run carries on while the question stands, so it goes on reporting;
    those reports queue on the interface thread while the dialog holds it. They
    arrive the moment the dialog closes, after the stop has been asked for.
    A bar that took them would go straight back to counting, which is what a
    stop that had not worked would look like.
    """
    window = make_window(application)
    window._discovery_runner = RunnerInProgress()
    answer(monkeypatch, QMessageBox.StandardButton.Yes)
    window.open_discovery()
    window.discovery_progressed(
        DiscoveryProgress(artist="Howlin' Wolf", done=8, total=31)
    )
    assert window._tray.discovery_bar.format() == STOPPING
