"""Telling a discovery run to stop; the run actually stopping.

Split from `test_discovery.py` on 2026-09-08, when that file reached the 381 to
399 danger band; the seam is the one the interface side already has in
`tests/ui/test_discovery_stopping.py`, whose name this deliberately does not
share: two test modules of one basename collide at collection, since these
directories carry no `__init__.py`. Over there is what a press does to the
window; here is what a cancel does to the run underneath it.

The requirement was amended three times in one day after the stop was reported
as not working, so what these hold is narrow on purpose: the run is consulted
before EVERY request rather than once an artist; a stop lands inside a wait
rather than at the end of one.
"""

from __future__ import annotations

from discovery_support import (
    ROCK,
    Catalogue,
    Similarity,
    Stopping,
    make_album,
    nothing,
)
from test_discovery import SLICES_BEFORE_STOP, make_run

from stellody.application.asking import (
    RETRY_ATTEMPTS,
    RETRY_PAUSE_SECONDS,
    WAIT_SLICE_SECONDS,
)
from stellody.application.values import RunOutcome
from stellody.domain.discovery import SimilarArtist


def test_cancel_stops_before_the_next_request() -> None:
    """Between requests rather than mid-flight, so nothing is half-written."""
    run, catalogue, _, _ = make_run()
    report = run.run((make_album("One", "A"),), ROCK, nothing, lambda: True)
    assert report.outcome is RunOutcome.CANCELLED
    assert not report.is_writable
    assert catalogue.identified == []


def test_closing_stops_the_run() -> None:
    """A close is a cancel expressed differently; it gets the same answer.

    Nothing is asked at all here. The run consults the cancel once for the
    artist and again before the request about that artist, so a stop arriving
    between those two lands before anything goes out. That is stronger than
    this asserted while the run only asked once an artist, when the request
    already under way went out regardless.
    """
    asked: list[bool] = []

    def once_around() -> bool:
        """False the first time, then True: the window closes mid-run."""
        asked.append(True)
        return len(asked) > 1

    run, catalogue, _, _ = make_run()
    albums = (make_album("One", "A"), make_album("Two", "B"))
    report = run.run(albums, ROCK, nothing, once_around)
    assert report.outcome is RunOutcome.CANCELLED
    assert catalogue.identified == []


class Pressed:
    """A cancel somebody can press between one question and the next."""

    def __init__(self) -> None:
        self.stopped = False

    def __call__(self) -> bool:
        """Whether the run has been told to stop."""
        return self.stopped


def test_the_question_handed_down_is_the_cancel_turned_round() -> None:
    """A predicate wired the wrong way round abandons every request at once.

    The run asks whether it has been CANCELLED; a client asks whether its
    answer is still WANTED. The two are opposites, so the one place they meet
    is worth an assertion of its own: nothing else in a passing run would
    notice the sense being inverted.
    """
    cancel = Pressed()
    run, catalogue, _, _ = make_run()
    run.run((make_album("One", "A"),), ROCK, nothing, cancel)
    handed = catalogue.wanted[0]
    assert handed() is True, "still wanted while nobody has pressed anything"
    cancel.stopped = True
    assert handed() is False, "not wanted the moment the run is stopped"


def test_cancelling_while_candidates_are_narrowed_writes_nothing() -> None:
    """The second phase is the long one, so it has to be stoppable too."""
    steps: list[bool] = []

    def after_the_first_artist() -> bool:
        """False while artists are gathered, True once narrowing starts."""
        steps.append(True)
        return len(steps) > 1

    offered = (SimilarArtist(name="Someone", identifier="someone"),)
    run, _, _, _ = make_run(similarity=Similarity(offered))
    report = run.run((make_album("One", "A"),), ROCK, nothing, after_the_first_artist)
    assert report.outcome is RunOutcome.CANCELLED


def test_a_stop_is_felt_part_way_through_a_wait() -> None:
    """The defect this exists for: stop pressed, nothing happening for seconds.

    Waiting out two refusals is six seconds, once taken in whole naps of two
    and four. A stop pressed at the start of the four second one
    was not acted on until it ended, which reads as a button that does not
    work. The wait is sliced now, so what is spent after the press is one
    slice rather than the rest of the nap.
    """
    catalogue = Catalogue(refusals=RETRY_ATTEMPTS)
    run, _, _, waits = make_run(catalogue)
    report = run.run(
        (make_album("U2", "A"),), ROCK, nothing, Stopping(after=SLICES_BEFORE_STOP)
    )
    assert report.outcome is RunOutcome.CANCELLED
    assert sum(waits.waited) <= WAIT_SLICE_SECONDS * SLICES_BEFORE_STOP
    assert sum(waits.waited) < RETRY_PAUSE_SECONDS, "it did not sit out the wait"


def test_a_stopped_run_asks_the_catalogue_nothing_further() -> None:
    """FR-D17: no further request is issued once somebody has stopped it."""
    catalogue = Catalogue(refusals=RETRY_ATTEMPTS)
    run, source, _, _ = make_run(catalogue)
    run.run((make_album("U2", "A"),), ROCK, nothing, Stopping(after=SLICES_BEFORE_STOP))
    assert source.identified == ["U2"], "it asked once and never again"


def test_a_stop_lands_between_requests_rather_than_between_artists() -> None:
    """The defect reported twice: a stop that took minutes to be felt.

    One artist costs three requests, each of which may take the full twenty
    second timeout and may be attempted three times. Asked once an artist, a
    run could go on for minutes after being told to stop; asked before every
    request, what is left is the one already in flight.
    """
    catalogue = Catalogue(identities={"U2": ("u2-id",)})
    run, source, similarity, _ = make_run(catalogue)
    # False for the artist, false for the first request, true after it: the
    # stop arrives while the run is between the first and second requests.
    stopping = Stopping(after=2)
    report = run.run((make_album("U2", "A"),), ROCK, nothing, stopping)
    assert report.outcome is RunOutcome.CANCELLED
    assert source.identified == ["U2"], "the one already asked"
    assert source.albums_asked == [], "and not the two that would have followed"
    assert similarity.asked == []
