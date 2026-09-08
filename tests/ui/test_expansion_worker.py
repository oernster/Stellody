"""Asking about one candidate artist, on a thread of its own.

The dialog's own suite drives the runner end to end, which proves the answer
arrives; it says nothing about the corners. These are the corners: a question
given up on, the same question asked twice, then closing while one is still in
flight.

The worker is driven DIRECTLY here rather than through a thread wherever the
point is what it does with an answer. A worker run on the interface thread is
the same object doing the same work; what a thread adds is where it happens,
which the dialog's suite exercises and coverage cannot see from here.
"""

from __future__ import annotations

from results_support import Catalogue, Slow, expansion, heard, waited_for

from stellody.domain.discovery import ReleaseGroup
from stellody.ui.expansion_worker import ExpansionRunner, ExpansionWorker
from stellody.ui.results_words import WENT_WRONG


def test_a_worker_says_what_the_artist_released(application) -> None:
    """The ordinary answer, which is one signal carrying who it is about."""
    album = ReleaseGroup(title="Aerial")
    worker = ExpansionWorker(expansion(Catalogue(albums=(album,))), "id-kb")
    said = heard(worker.ready)
    worker.run()
    assert said == [("id-kb", (album,))]


def test_a_worker_says_what_went_wrong_rather_than_dying_quietly(application) -> None:
    """An artist whose lookup died in silence would sit open and empty."""
    worker = ExpansionWorker(expansion(Catalogue(raises=RuntimeError("no"))), "id-x")
    failed, ready = heard(worker.failed), heard(worker.ready)
    worker.run()
    assert failed == [("id-x", WENT_WRONG)]
    assert ready == []


def test_the_row_gets_words_and_the_log_gets_the_machine(application) -> None:
    """Reported by Oliver on 2026-09-08, shown a row naming a Qt error and a
    MusicBrainz URL: unreadable to anybody who did not write this; the only
    thing worth having to whoever has to fix it. So both are kept, apart."""
    written: list[str] = []
    worker = ExpansionWorker(
        expansion(Catalogue(raises=RuntimeError("Qt said no"))),
        "id-x",
        written.append,
    )
    failed = heard(worker.failed)
    worker.run()
    assert failed == [("id-x", WENT_WRONG)], "the row says what to do"
    assert len(written) == 1
    assert "RuntimeError" in written[0], "the log says what happened"
    assert "Qt said no" in written[0]
    assert "id-x" in written[0], "and which artist it happened to"


def test_a_cancelled_worker_carries_the_giving_up_into_the_request(
    application,
) -> None:
    """The question goes down WITH the request, so a stop is felt inside it."""
    catalogue = Catalogue(albums=())
    worker = ExpansionWorker(expansion(catalogue), "id-x")
    worker.cancel()
    worker.run()
    assert catalogue.asked == []


def test_the_same_question_is_not_asked_twice_at_once(application) -> None:
    """A second press on an artist already being looked up is not a second ask."""
    catalogue = Slow()
    runner = ExpansionRunner(expansion(catalogue))
    try:
        assert runner.ask("id-slow")
        assert waited_for(application, lambda: catalogue.entered)
        assert not runner.ask("id-slow")
        assert runner.asking_about("id-slow")
    finally:
        runner.stop()


def test_stopping_lets_go_of_a_question_still_in_flight(application) -> None:
    """A thread still running when Qt tears its owner down ends the process."""
    catalogue = Slow()
    runner = ExpansionRunner(expansion(catalogue))
    assert runner.ask("id-slow")
    assert waited_for(application, lambda: catalogue.entered)
    runner.stop()
    assert not runner.asking_about("id-slow")


def test_an_answer_about_an_artist_nobody_is_waiting_for_is_harmless(
    application,
) -> None:
    """A question stopped and then answered anyway has no thread left to tidy."""
    runner = ExpansionRunner(expansion(Catalogue()))
    runner._on_ready("id-nobody", ())
    runner._on_failed("id-nobody", "nothing answered at all")
    assert not runner.asking_about("id-nobody")
