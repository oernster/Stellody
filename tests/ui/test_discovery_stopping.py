"""What the tray does while a discovery run is under way.

Split from the endings suite beside it when that module reached the line cap.
The seam is the one the feature already has: what is SAID about a run that has
ended against what is SHOWN while one is still going.
"""

from __future__ import annotations

import threading
import time

import pytest
from discovery_wiring_support import (
    RunnerInProgress,
    a_report,
    make_window,
)
from PySide6.QtCore import QSize, qInstallMessageHandler
from PySide6.QtGui import QImage
from PySide6.QtWidgets import QMessageBox, QPushButton

from stellody.application.values import DiscoveryProgress, RunOutcome, RunReport
from stellody.ui.discovering import STILL_STOPPING
from stellody.ui.discovery_progress import RESTING
from stellody.ui.discovery_worker import DiscoveryRunner
from stellody.ui.tray_metrics import (
    DISCOVER_TOOLTIP,
    ICON_PX,
    STOP_DISCOVERY_TOOLTIP,
    show_discovery_running,
)

# What a stop is allowed to take. Oliver's ruling is one to two seconds, so a
# fifth of that leaves room for a slow machine while still failing the twenty
# second wait this exists to stop coming back.
STOP_LIMIT_S = 0.5
# How long a wedged run waits before giving up on its own, so a test that goes
# wrong ends rather than hanging the suite.
WEDGED_LIMIT_S = 10
# Long enough that a run is genuinely under way when it is abandoned, short
# enough that it ends while the test is still watching it.
BRIEF_RUN_S = 0.3
# How long to let an abandoned thread finish before giving up on it.
SETTLE_LIMIT_S = 5.0
SETTLE_SLICE_S = 0.01


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
    window.open_discovery()
    assert runner.stopped == 1, "it cancelled rather than opening a second dialog"


def test_a_press_stops_at_once_without_asking_anything(
    application, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The defect, reported three times and finally traced on 2026-09-07.

    A stop used to raise a question defaulting to No. A trace of the real
    application caught it answering False while the run carried straight on,
    which is what "it never stops" was: the machinery underneath had been
    working the whole time and no press ever reached it.

    So this asserts the absence of the question as well as the presence of the
    stop. Asserting only that the run stopped would pass again the day
    somebody reintroduces a dialog that a listener has to get past.
    """
    asked: list[object] = []
    monkeypatch.setattr(
        QMessageBox, "question", lambda *arguments, **named: asked.append(arguments)
    )
    window = make_window(application)
    runner = RunnerInProgress()
    window._discovery_runner = runner
    window.discovery_progressed(
        DiscoveryProgress(artist="Muddy Waters", done=1, total=4)
    )
    window.open_discovery()
    assert asked == [], "nothing stands between the press and the stop"
    assert runner.stopped == 1, "and the run was actually stopped"
    assert window._tray.discovery_bar.format() == RESTING


def shown(button) -> QImage:
    """What the button is actually displaying, as pixels rather than an object.

    Two QIcons built from the same file are different objects with different
    cache keys, so identity says nothing. The picture does.
    """
    return button.icon().pixmap(QSize(ICON_PX, ICON_PX)).toImage()


def references() -> tuple[QImage, QImage]:
    """What a resting button looks like and what a running one looks like.

    Taken from the helper itself rather than from the button's starting state,
    since the tray in these tests builds its buttons without artwork: a test
    that measured against that would be comparing every ending to an empty
    picture and would pass whatever the button ended up wearing.
    """
    spare = QPushButton()
    show_discovery_running(spare, False)
    resting = shown(spare)
    show_discovery_running(spare, True)
    running = shown(spare)
    assert resting != running, "the cross has to make a visible difference"
    return resting, running


def test_the_button_wears_the_cross_while_a_run_is_under_way(
    application,
) -> None:
    """One button carries both meanings, so it has to show which it carries."""
    _, running = references()
    window = make_window(application)
    window._discovery_runner = RunnerInProgress()
    window.begin_discovery(("Rock",))
    assert shown(window._tray.discover_button) == running, "the cross is on"
    assert window._tray.discover_button.toolTip() == STOP_DISCOVERY_TOOLTIP


def test_the_cross_comes_off_when_a_run_is_stopped(application) -> None:
    """A button still crossed out after a stop offers to stop nothing."""
    resting, _ = references()
    window = make_window(application)
    window._discovery_runner = RunnerInProgress()
    window.begin_discovery(("Rock",))
    window.open_discovery()
    assert shown(window._tray.discover_button) == resting
    assert window._tray.discover_button.toolTip() == DISCOVER_TOOLTIP


def test_the_cross_comes_off_when_a_run_finishes_on_its_own(application) -> None:
    """Asked for on 2026-09-07: every ending clears it, not only a stop."""
    resting, _ = references()
    window = make_window(application)
    window._discovery_runner = RunnerInProgress()
    window.begin_discovery(("Rock",))
    window.discovery_completed(a_report(albums=0, artists=0))
    assert shown(window._tray.discover_button) == resting
    assert window._tray.discover_button.toolTip() == DISCOVER_TOOLTIP


def test_the_cross_comes_off_when_a_run_fails(application) -> None:
    """A run nobody could reach is an ending like any other."""
    resting, _ = references()
    window = make_window(application)
    window._discovery_runner = RunnerInProgress()
    window.begin_discovery(("Rock",))
    window.discovery_failed("nothing answered")
    assert shown(window._tray.discover_button) == resting
    assert window._tray.discover_button.toolTip() == DISCOVER_TOOLTIP


def test_a_stop_lets_go_of_the_run_at_once(
    application, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Ruled on 2026-09-07: the bar resets on the press, not on the ending.

    A request already in flight cannot be called back and may take the full
    twenty second timeout, so a bar held until the run noticed would go on
    reporting a run somebody had already finished with.
    """
    window = make_window(application)
    runner = RunnerInProgress()
    window._discovery_runner = runner
    window.discovery_progressed(
        DiscoveryProgress(artist="Muddy Waters", done=1, total=4)
    )
    window.open_discovery()
    assert runner.stopped == 1
    assert window._tray.discovery_bar.format() == RESTING
    assert window._tray.discovery_bar.value() == 0
    assert window._tray.discover_button.toolTip() == DISCOVER_TOOLTIP


def test_progress_reported_after_a_stop_does_not_revive_the_bar(
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
    window.open_discovery()
    window.discovery_progressed(
        DiscoveryProgress(artist="Howlin' Wolf", done=8, total=31)
    )
    assert window._tray.discovery_bar.format() == RESTING


class RunnerThatWillNotStart:
    """A runner still winding down, which refuses to take a second run."""

    running = False

    def __init__(self) -> None:
        self.asked = 0

    def start(self, *_arguments) -> bool:
        """Refuse, as the real one does while its thread is still going."""
        self.asked += 1
        return False

    def cancel(self) -> None:
        """Never reached in these tests."""


def test_a_new_run_asked_for_too_soon_says_so(application) -> None:
    """The trap the reset opened, closed before anybody could fall into it.

    Letting go of a stopped run at once means the button is offering to start
    another while the thread is still winding down. The runner refuses that;
    a refusal nobody is told about is a press that does nothing, which is the
    defect this whole area was reported for.
    """
    window = make_window(application)
    window._discovery_runner = RunnerThatWillNotStart()
    window.begin_discovery(("Blues",))
    assert window._status.said == [STILL_STOPPING]


def test_a_stopped_run_does_not_announce_itself_when_it_finally_ends(
    application, monkeypatch: pytest.MonkeyPatch
) -> None:
    """It was reported on when it was stopped, which is what was asked."""
    window = make_window(application)
    window._discovery_runner = RunnerInProgress()
    window.open_discovery()
    said_when_stopped = list(window._status.said)
    window.discovery_completed(a_report(albums=2, artists=3))
    assert window._status.said == said_when_stopped, "it did not speak twice"


class Wedged:
    """A run that will not end, standing in for a service that will not answer.

    The case a stop has to survive: not a run between requests, rather one
    blocked inside a request nobody can call back.
    """

    def __init__(self) -> None:
        self.let_go = threading.Event()

    def run(self, _albums, _ticked, _report, _cancelled):
        """Sit there until the test says otherwise."""
        self.let_go.wait(WEDGED_LIMIT_S)
        return RunReport(outcome=RunOutcome.COMPLETED)


def test_a_stop_is_instant_even_while_a_request_is_wedged(application) -> None:
    """Ruled on 2026-09-07: a stop means stop, not stop within twenty seconds.

    Driven through the real runner and a real thread rather than a stand-in,
    because what is asserted is precisely the thing a stand-in would fake: that
    the stop does not wait for the run. The run here cannot be hurried at all,
    which is the worst case a listener meets when a service stops answering.
    """
    wedged = Wedged()
    runner = DiscoveryRunner()
    try:
        assert runner.start(wedged, (), ("Blues",))
        started = time.monotonic()
        runner.cancel()
        assert time.monotonic() - started < STOP_LIMIT_S
        assert not runner.running, "the runner is free for another run at once"
        assert runner.start(wedged, (), ("Folk",)), "and takes one"
    finally:
        wedged.let_go.set()
        runner.wait()


class Briefly:
    """A run that takes a moment and then ends of its own accord.

    It says when it has actually begun. Measured on 2026-09-07: a cancel that
    arrives before the worker has started is a different case entirely; the
    fault this is here to catch cannot happen in it. Waiting on the run itself
    rather than on a length of time keeps that out of the hands of whichever
    machine the suite runs on.
    """

    def __init__(self) -> None:
        self.began = threading.Event()

    def run(self, albums, ticked, report, cancelled):
        """Work for a while, noticing a cancel the way a real run does."""
        self.began.set()
        deadline = time.monotonic() + BRIEF_RUN_S
        while time.monotonic() < deadline:
            if cancelled():
                return RunReport(outcome=RunOutcome.CANCELLED)
            time.sleep(SETTLE_SLICE_S)
        return RunReport(outcome=RunOutcome.COMPLETED)


def test_an_abandoned_run_lets_go_of_its_thread_without_qt_complaining(
    application,
) -> None:
    """A signal connected to a bare callable runs in the SENDER'S thread.

    The abandon path connected the worker's ending to a lambda, so the tidying
    up ran ON the thread being tidied and asked it to wait for itself. Qt
    refused and said so twice in Oliver's session on 2026-09-07; the list of
    abandoned threads was being edited off the interface thread at the same
    time, which said nothing at all.

    Qt's own complaint is the assertion, since neither fault raises: the wait
    returns false and the edit is a race that usually gets away with it. A test
    reading only the outcome would have passed throughout.
    """
    said: list[str] = []
    previous = qInstallMessageHandler(
        lambda mode, context, message: said.append(message)
    )
    runner = DiscoveryRunner()
    briefly = Briefly()
    try:
        assert runner.start(briefly, (), ("Blues",))
        assert briefly.began.wait(SETTLE_LIMIT_S), "the run is genuinely under way"
        runner.cancel()
        deadline = time.monotonic() + SETTLE_LIMIT_S
        while time.monotonic() < deadline and runner._abandoned:
            application.processEvents()
            time.sleep(SETTLE_SLICE_S)
        application.processEvents()
    finally:
        runner.wait()
        qInstallMessageHandler(previous)
    assert [
        heard for heard in said if "wait on itself" not in heard
    ] == said, f"Qt complained about the thread being let go of: {said}"
    assert not runner._abandoned, "and the thread was actually released"
