"""Driving a discovery from the window: what is said about each ending.

A run that found nothing, one nobody could reach, one somebody stopped and one
whose file would not write are four different things. A dialog that merely
stopped moving would tell somebody none of them apart, so each is asserted.
"""

from __future__ import annotations

from PySide6.QtCore import QObject
from PySide6.QtWidgets import QPushButton, QWidget

from stellody.application.values import DiscoveryProgress, RunOutcome, RunReport
from stellody.domain.discovery import Gaps, ReleaseGroup, SimilarArtist
from stellody.ui.discovering import (
    COULD_NOT_WRITE,
    FOUND,
    FOUND_NOTHING,
    NOTHING_TO_ASK,
    STOPPED,
    UNREACHABLE,
    WENT_WRONG,
    Discovering,
)
from stellody.ui.discovery_progress import RESTING, STOPPING, DiscoveryBar
from stellody.ui.discovery_worker import DiscoveryRunner
from stellody.ui.tray_metrics import (
    BUTTON_PX,
    DISCOVER_TOOLTIP,
    STOP_DISCOVERY_TOOLTIP,
)

WHERE = "C:/somewhere/discovered.json"


class Tray:
    """Just enough tray to hold the two things the mixin touches.

    The bar is the real one rather than a stand-in, since what the mixin does
    with it is the whole point of the change that put it there.
    """

    def __init__(self, parent: QWidget) -> None:
        self.discover_button = QPushButton(parent)
        self.discovery_bar = DiscoveryBar(parent, BUTTON_PX)


class StatusBar:
    """A status bar that only remembers what it was told to say."""

    def __init__(self) -> None:
        self.said: list[str] = []

    def showMessage(self, message: str) -> None:
        """Qt's own spelling, since the mixin calls Qt's own method."""
        self.said.append(message)


class Window(Discovering, QObject):
    """The mixin over nothing else, which is all it needs to be driven.

    The holder is kept on the window rather than left as a local: a parent
    that goes out of scope is collected, taking the button with it.
    """

    def __init__(self) -> None:
        super().__init__()
        self._all_albums = ()
        self._holder = QWidget()
        self._tray = Tray(self._holder)
        self._status = StatusBar()

    def statusBar(self) -> StatusBar:
        """Where an ended run is announced now that no dialog is open."""
        return self._status


class RunnerInProgress:
    """A runner that is always mid-run and only records being stopped.

    Hand written rather than a real runner held open: a test that had to keep
    a thread alive to assert what a button does would be a test of the thread.
    """

    running = True

    def __init__(self) -> None:
        self.stopped = 0

    def cancel(self) -> None:
        """Record that stopping was asked for."""
        self.stopped += 1


class Service:
    """A discovery service that is never actually asked anything."""

    def run(self, albums, ticked, report, cancelled):
        """Stand in for a run; the wiring tests never reach this."""
        return RunReport(outcome=RunOutcome.COMPLETED)


def wrote(report: RunReport) -> str:
    """A writer that always succeeds, answering where it put it."""
    return WHERE


def refused(report: RunReport) -> str:
    """A writer that will not, the way a full disk will not."""
    raise OSError("no room")


def a_report(albums: int = 1, artists: int = 1) -> RunReport:
    """A completed run holding this much."""
    return RunReport(
        outcome=RunOutcome.COMPLETED,
        gaps=(
            Gaps(
                artist="U2",
                albums=tuple(ReleaseGroup(title=f"Album {n}") for n in range(albums)),
                artists=tuple(
                    SimilarArtist(name=f"Artist {n}") for n in range(artists)
                ),
            ),
        ),
    )


def make_window(application, write=wrote, service=None) -> Window:
    """A window mixin wired to a service and a writer."""
    window = Window()
    window.start_discovering(service if service is not None else Service(), write=write)
    return window


def test_nothing_to_ask_says_so(application) -> None:
    """Ticking a genre nothing carries is an ordinary thing to do."""
    window = make_window(application)
    assert window._settled(RunReport(outcome=RunOutcome.NOTHING_TO_ASK)) == (
        NOTHING_TO_ASK
    )


def test_a_stopped_run_says_nothing_was_written(application) -> None:
    """A cancel discards; the earlier answer is left alone."""
    window = make_window(application)
    assert window._settled(RunReport(outcome=RunOutcome.CANCELLED)) == STOPPED


def test_nothing_answering_says_to_try_again(application) -> None:
    """No connection is a different thing from nothing being missing."""
    window = make_window(application)
    assert window._settled(RunReport(outcome=RunOutcome.UNAVAILABLE)) == UNREACHABLE


def test_a_run_that_found_things_writes_them_and_counts_them(application) -> None:
    """The counts are what somebody actually wants to know."""
    window = make_window(application)
    said = window._settled(a_report(albums=2, artists=3))
    assert said == FOUND.format(albums=2, artists=3, where=WHERE)


def test_a_run_that_found_nothing_writes_nothing(application) -> None:
    """An empty answer is not worth replacing a file over."""
    window = make_window(application)
    assert window._settled(a_report(albums=0, artists=0)) == FOUND_NOTHING


def test_a_file_that_will_not_write_is_reported(application) -> None:
    """With the reason, plus any earlier answer left where it was."""
    window = make_window(application, write=refused)
    said = window._settled(a_report())
    assert said.startswith("The answer could not be written")
    assert COULD_NOT_WRITE.format(reason="no room") == said


def test_a_window_with_no_writer_keeps_quiet_about_files(application) -> None:
    """A window given no writer still runs; it has nowhere to put an answer."""
    window = make_window(application, write=None)
    assert window._settled(a_report()) == FOUND_NOTHING


def test_a_run_that_fell_over_says_why(application) -> None:
    """Ending the thread in silence leaves a bar spinning for ever."""
    window = make_window(application)
    window._discovery_dialog = None
    window.discovery_failed("the roof fell in")
    assert WENT_WRONG.format(reason="the roof fell in")


def test_the_button_is_dead_where_there_is_no_service(application) -> None:
    """There and disabled rather than there and doing nothing."""
    window = make_window(application, service=None)
    window.start_discovering(None, None)
    window.show_discovery_offer()
    assert not window._tray.discover_button.isEnabled()


def test_the_button_is_alive_where_there_is_one(application) -> None:
    """The other half of the same rule."""
    window = make_window(application)
    window.show_discovery_offer()
    assert window._tray.discover_button.isEnabled()


def test_a_window_with_no_service_starts_nothing(application) -> None:
    """Guarded rather than merely disabled, since the keyboard reaches it."""
    window = make_window(application)
    window.start_discovering(None, None)
    window.begin_discovery(("Rock",))
    assert not window._discovery_runner.running
    window.open_discovery()


def test_the_runner_reports_a_finished_run(application) -> None:
    """The report crosses back on the interface thread, not the worker's."""
    seen: list[RunReport] = []
    runner = DiscoveryRunner()
    runner.completed.connect(seen.append)
    assert runner.start(Service(), (), ("Rock",))
    runner.wait()
    application.processEvents()
    assert not runner.running
    assert len(seen) == 1


def test_the_runner_refuses_a_second_run(application) -> None:
    """One run at a time, guarded where the thread actually lives."""
    runner = DiscoveryRunner()
    assert runner.start(Service(), (), ("Rock",))
    assert not runner.start(Service(), (), ("Rock",))
    runner.wait()
    application.processEvents()


def test_cancelling_nothing_is_harmless(application) -> None:
    """A stop asked of a runner with nothing running must not raise."""
    runner = DiscoveryRunner()
    runner.cancel()
    runner.wait()
    assert not runner.running


def test_a_run_that_raises_is_reported_rather_than_silent(application) -> None:
    """A worker that ended in silence would leave a dialog waiting for ever."""

    class Falling:
        """A service that cannot get through a run."""

        def run(self, albums, ticked, report, cancelled):
            """Fail the way an unanticipated fault would."""
            raise RuntimeError("the roof fell in")

    said: list[str] = []
    runner = DiscoveryRunner()
    runner.failed.connect(said.append)
    runner.start(Falling(), (), ("Rock",))
    runner.wait()
    application.processEvents()
    assert said == ["the roof fell in"]


def test_an_ending_is_announced_where_a_dialog_no_longer_is(application) -> None:
    """The dialog closed when the run started, so the strip says how it ended."""
    window = make_window(application)
    window.discovery_completed(a_report(albums=2, artists=3))
    assert window._status.said == [FOUND.format(albums=2, artists=3, where=WHERE)]


def test_an_ending_puts_the_bar_and_the_button_back(application) -> None:
    """However a run ended, the tray stops offering to stop it."""
    window = make_window(application)
    window.discovery_progressed(
        DiscoveryProgress(artist="Muddy Waters", done=1, total=4)
    )
    window.discovery_failed("the roof fell in")
    assert window._tray.discovery_bar.format() == RESTING
    assert window._tray.discover_button.toolTip() == DISCOVER_TOOLTIP


def test_progress_is_drawn_in_the_tray(application) -> None:
    """It reports where the run is watched from now, which is the strip."""
    window = make_window(application)
    window.discovery_progressed(
        DiscoveryProgress(artist="Muddy Waters", done=1, total=4)
    )
    assert window._tray.discovery_bar.value() == 25
    assert "Muddy Waters" in window._tray.discovery_bar.toolTip()


def test_a_started_run_turns_the_button_into_a_stop(application) -> None:
    """One control carries both meanings once the dialog has gone."""
    window = make_window(application)
    window.begin_discovery(("Rock",))
    try:
        assert window._tray.discover_button.toolTip() == STOP_DISCOVERY_TOOLTIP
    finally:
        window._discovery_runner.wait()


def test_pressing_it_during_a_run_stops_the_run(application) -> None:
    """The whole reason the button changes meaning rather than going dead."""
    window = make_window(application)
    runner = RunnerInProgress()
    window._discovery_runner = runner
    window.open_discovery()
    assert runner.stopped == 1, "it cancelled rather than opening a second dialog"


def test_a_stop_is_acknowledged_before_the_run_has_stopped(application) -> None:
    """A run gives up between requests, so the press lands before the ending."""
    window = make_window(application)
    runner = RunnerInProgress()
    window._discovery_runner = runner
    window.discovery_progressed(
        DiscoveryProgress(artist="Muddy Waters", done=1, total=4)
    )
    window.open_discovery()
    assert window._tray.discovery_bar.format() == STOPPING
    assert runner.stopped == 1
