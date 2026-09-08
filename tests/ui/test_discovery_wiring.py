"""Driving a discovery from the window: what is said about each ending.

A run that found nothing, one nobody could reach, one somebody stopped and one
whose file would not write are four different things. A dialog that merely
stopped moving would tell somebody none of them apart, so each is asserted.
"""

from __future__ import annotations

from discovery_wiring_support import (
    WHERE,
    Service,
    a_report,
    make_window,
    refused,
)

from stellody.application.values import DiscoveryProgress, RunOutcome, RunReport
from stellody.ui.discovering import (
    COULD_NOT_WRITE,
    FOUND,
    FOUND_NOTHING,
    NOTHING_TO_ASK,
    STOPPED,
    UNREACHABLE,
    WENT_WRONG,
)
from stellody.ui.discovery_worker import DiscoveryRunner
from stellody.ui.tray_metrics import (
    DISCOVER_TOOLTIP,
)


def test_nothing_to_ask_says_so(application) -> None:
    """Ticking a genre nothing carries is an ordinary thing to do."""
    window = make_window(application)
    assert window._settled(RunReport(outcome=RunOutcome.NOTHING_TO_ASK)) == (
        NOTHING_TO_ASK,
        False,
    )


def test_a_stopped_run_says_nothing_was_written(application) -> None:
    """A cancel discards; the earlier answer is left alone."""
    window = make_window(application)
    assert window._settled(RunReport(outcome=RunOutcome.CANCELLED)) == (
        STOPPED,
        False,
    ), "a stopped run leaves the earlier file alone, so it opens nothing"


def test_nothing_answering_says_to_try_again(application) -> None:
    """No connection is a different thing from nothing being missing."""
    window = make_window(application)
    assert window._settled(RunReport(outcome=RunOutcome.UNAVAILABLE)) == (
        UNREACHABLE,
        False,
    ), "nothing was written, so there is nothing of this run's to show"


def test_a_run_that_found_things_writes_them_and_counts_them(application) -> None:
    """The counts are what somebody actually wants to know."""
    window = make_window(application)
    said, found = window._settled(a_report(albums=2, artists=3))
    assert said == FOUND.format(albums=2, artists=3, where=WHERE)
    assert found, "a run that wrote a file has something worth opening"


def test_a_run_that_found_nothing_writes_nothing(application) -> None:
    """An empty answer is not worth replacing a file over."""
    window = make_window(application)
    assert window._settled(a_report(albums=0, artists=0)) == (FOUND_NOTHING, False)


def test_a_file_that_will_not_write_is_reported(application) -> None:
    """With the reason, plus any earlier answer left where it was."""
    window = make_window(application, write=refused)
    said, found = window._settled(a_report())
    assert said.startswith("The answer could not be written")
    assert COULD_NOT_WRITE.format(reason="no room") == said
    assert not found, "a file that would not write has nothing to show from"


def test_a_window_with_no_writer_keeps_quiet_about_files(application) -> None:
    """A window given no writer still runs; it has nowhere to put an answer."""
    window = make_window(application, write=None)
    assert window._settled(a_report()) == (FOUND_NOTHING, False)


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
    assert window._tray.discovery_bar.resting
    assert window._tray.discover_button.toolTip() == DISCOVER_TOOLTIP


def test_progress_is_drawn_in_the_tray(application) -> None:
    """It reports where the run is watched from now, which is the strip."""
    window = make_window(application)
    window.discovery_progressed(
        DiscoveryProgress(artist="Muddy Waters", done=1, total=4)
    )
    assert window._tray.discovery_bar.looking_up.value() == 25
    assert "Muddy Waters" in window._tray.discovery_bar.toolTip()
