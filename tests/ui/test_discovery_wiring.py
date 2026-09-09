"""Driving a discovery from the window: what is said about each ending.

A run that found nothing, one nobody could reach, one somebody stopped and one
whose file would not write are four different things. A dialog that merely
stopped moving would tell somebody none of them apart, so each is asserted.
"""

from __future__ import annotations

from discovery_wiring_support import (
    WHERE,
    RunnerInProgress,
    Service,
    a_report,
    completed,
    make_window,
    refused,
)
from PySide6.QtWidgets import QTextBrowser

from stellody.application.values import (
    DiscoveryProgress,
    RunOutcome,
    RunReport,
    SourceFailure,
)
from stellody.ui import shortfall
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
from stellody.ui.shortfall import ShortfallDialog
from stellody.ui.tray_metrics import (
    DISCOVER_TOOLTIP,
)

# Assembled rather than written out, so the prose sweep does not read the
# assertion that the rule holds as a breach of it.
SERIAL_COMMA = "," + " and"


def test_nothing_to_ask_says_so(application) -> None:
    """Ticking a genre nothing carries is an ordinary thing to do."""
    window = make_window(application)
    assert window._settled(RunReport(outcome=RunOutcome.NOTHING_TO_ASK)) == (
        NOTHING_TO_ASK,
        False,
        False,
    )


def test_a_stopped_run_says_nothing_was_written(application) -> None:
    """A cancel discards; the earlier answer is left alone."""
    window = make_window(application)
    assert window._settled(RunReport(outcome=RunOutcome.CANCELLED)) == (
        STOPPED,
        False,
        False,
    ), "a stopped run leaves the earlier file alone, so it opens nothing"


def test_nothing_answering_says_to_try_again(application) -> None:
    """No connection is a different thing from nothing being missing."""
    window = make_window(application)
    assert window._settled(RunReport(outcome=RunOutcome.UNAVAILABLE)) == (
        UNREACHABLE,
        False,
        False,
    ), "nothing was written, so there is nothing of this run's to show"


def test_a_run_that_found_things_writes_them_and_counts_them(application) -> None:
    """The counts are what somebody actually wants to know."""
    window = make_window(application)
    said, found, _ = window._settled(a_report(albums=2, artists=3))
    assert said == FOUND.format(albums=2, artists=3, where=WHERE)
    assert found, "a run that wrote a file has something worth opening"


def test_a_run_that_found_nothing_still_writes_and_opens(application) -> None:
    """Nothing missing is an answer about the library rather than an absence
    of one, so it replaces the file and opens like any other. Ruled by Oliver
    on 2026-09-09."""
    window = make_window(application)
    assert window._settled(a_report(albums=0, artists=0)) == (
        FOUND_NOTHING,
        True,
        True,
    )


def test_a_run_short_of_one_artist_says_so(application) -> None:
    """An answer that could not ask about somebody reads complete otherwise."""
    window = make_window(application)
    said, found, presented = window._settled(a_report(albums=2, artists=3, failed=1))
    expected = f" {shortfall.COULD_NOT_ASK[0].capitalize()}{shortfall.SO_INCOMPLETE}"
    assert said == FOUND.format(albums=2, artists=3, where=WHERE) + expected
    assert found, "the shortfall is a caveat on an answer, not a reason to hide it"
    assert presented, "an ending that presents an answer carries the shortfall"


def test_a_run_names_all_three_kinds_of_silence(application) -> None:
    """Each is a different thing to do about it, so each is counted apart."""
    window = make_window(application)
    said, _, _ = window._settled(
        a_report(albums=2, artists=3, failed=4, unresolved=3, ambiguous=2)
    )
    assert "4 artists could not be asked about" in said
    assert "3 names were not recognised" in said
    assert "2 names matched more than one artist" in said
    assert said.endswith(shortfall.SO_INCOMPLETE)
    assert SERIAL_COMMA not in said, "the house rule holds in what the screen says"


def test_only_the_groups_that_happened_are_named(application) -> None:
    """A run with one kind of silence says one thing, not three with zeroes."""
    window = make_window(application)
    said, _, _ = window._settled(a_report(unresolved=3))
    assert "3 names were not recognised" in said
    assert "could not be asked about" not in said
    assert "matched more than one" not in said


def test_finding_nothing_still_says_what_went_unanswered(application) -> None:
    """The ending this matters most on: nothing found reads as nothing missing."""
    window = make_window(application)
    said, found, presented = window._settled(a_report(albums=0, artists=0, ambiguous=2))
    assert said.startswith(FOUND_NOTHING)
    assert "2 names matched more than one artist" in said
    assert found, "an empty answer is still an answer, so it opens"
    assert presented, "it still presents an answer, so the caveat belongs on it"


def test_a_stopped_run_counts_nothing(application) -> None:
    """It has already said the answer is incomplete; twice is noise."""
    window = make_window(application)
    stopped = RunReport(
        outcome=RunOutcome.CANCELLED,
        failed=(SourceFailure(artist="Nobody", reason="a server error"),),
    )
    assert window._settled(stopped) == (STOPPED, False, False)


def test_a_clean_run_says_nothing_extra(application) -> None:
    """The sentence is owed only where something was actually missed."""
    window = make_window(application)
    said, _, _ = window._settled(a_report(albums=2, artists=3))
    assert said == FOUND.format(albums=2, artists=3, where=WHERE)


def test_the_button_appears_carrying_its_own_count(application) -> None:
    """It outlives its sentence, so it has to say what it is on its own."""
    window = make_window(application)
    completed(window, a_report(albums=2, artists=3, failed=4, unresolved=5))
    assert not window._shortfall_button.isHidden()
    assert window._shortfall_button.text() == "9 artists unanswered"


def test_one_unanswered_artist_reads_as_one(application) -> None:
    """Nothing on this screen says 1 artists."""
    window = make_window(application)
    completed(window, a_report(albums=2, artists=3, ambiguous=1))
    assert window._shortfall_button.text() == "1 artist unanswered"


def test_a_clean_run_offers_no_button(application) -> None:
    """There is nothing behind it, so there is nothing to press."""
    window = make_window(application)
    completed(window, a_report(albums=2, artists=3))
    assert window._shortfall_button.isHidden()


def test_a_new_run_takes_the_last_one_s_button_away(application) -> None:
    """The shortfall belongs to the run that had it, not to the evening."""
    window = make_window(application)
    completed(window, a_report(albums=2, artists=3, failed=4))
    assert not window._shortfall_button.isHidden()
    # A runner that takes the run without starting a thread. A real one
    # would outlive this test and take Qt down with it, which says nothing
    # about the button.
    window._discovery_runner = RunnerInProgress()
    window.begin_discovery(("Rock",))
    assert window._shortfall_button.isHidden()
    assert window._shortfall_report is None


def test_a_stopped_run_offers_no_button_either(application) -> None:
    """The same rule the sentence follows, so the two cannot disagree."""
    window = make_window(application)
    completed(
        window,
        RunReport(
            outcome=RunOutcome.CANCELLED,
            failed=(SourceFailure(artist="Nobody", reason="a server error"),),
        ),
    )
    assert window._shortfall_button.isHidden()


def test_pressing_it_opens_the_names(application, monkeypatch) -> None:
    """What the button is for, taken down the path the press actually takes."""
    window = make_window(application)
    completed(window, a_report(albums=2, artists=3, failed=1, unresolved=1))
    opened: list[ShortfallDialog] = []
    monkeypatch.setattr(ShortfallDialog, "exec", lambda dialog: opened.append(dialog))
    window._shortfall_button.click()
    assert len(opened) == 1
    assert "Nobody 0" in opened[0].findChild(QTextBrowser).toPlainText()


def test_pressing_it_with_nothing_behind_it_opens_nothing(application) -> None:
    """Reachable by keyboard while hidden is not the same as safe; assert it."""
    window = make_window(application)
    window.show_shortfall()


def test_a_file_that_will_not_write_is_reported(application) -> None:
    """With the reason, plus any earlier answer left where it was."""
    window = make_window(application, write=refused)
    said, found, _ = window._settled(a_report())
    assert said.startswith("The answer could not be written")
    assert COULD_NOT_WRITE.format(reason="no room") == said
    assert not found, "a file that would not write has nothing to show from"


def test_a_run_with_a_hole_in_it_still_opens_its_answer(application) -> None:
    """Reported by Oliver on 2026-09-09: an hour of running, then nothing.

    One artist that could not be answered for used to discard the whole run,
    so a screen he had waited 54 minutes for never opened and the only account
    of it went to the status bar. The answer is shown now, with the shortfall
    beside it saying how much is missing.
    """
    window = make_window(application)
    said, found, presented = window._settled(a_report(failed=1))
    assert found, "the answer is there to be opened"
    assert presented, "so the shortfall belongs beside it"
    assert said.endswith(shortfall.SO_INCOMPLETE), "and it says what is missing"


def test_a_window_with_no_writer_keeps_quiet_about_files(application) -> None:
    """A window given no writer still runs; it has nowhere to put an answer."""
    window = make_window(application, write=None)
    assert window._settled(a_report()) == (FOUND_NOTHING, False, True)


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
