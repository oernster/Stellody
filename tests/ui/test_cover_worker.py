"""Looking a cover up on a thread, then letting go of one nobody waits for.

The thread is real. What is stood in for is the archive underneath the service,
which would otherwise open a connection.

The last class here is the one worth reading. It holds the claim the module
docstring makes about cancelling: a request already in flight cannot be
interrupted, so what the runner promises is narrower than stopping it. It
promises the answer is DROPPED. That is asserted by holding a search open,
letting go of it, then releasing it and watching nothing arrive.
"""

from __future__ import annotations

import threading
import time

import pytest
from cover_support import BACK, FRONT, KEPT, FakeArtwork, FakeSearch, RaisingSearch
from PySide6.QtCore import QThread
from PySide6.QtWidgets import QApplication

from stellody.application.choosing_covers import ChooseCover
from stellody.domain.cover_choice import CoverOffer
from stellody.domain.identity import AlbumIdentity
from stellody.ui.cover_worker import CoverRunner, SearchWorker

PLANETS = AlbumIdentity(album_artist="Holst", title="The Planets")
ART_KEY = PLANETS.art_key
SETTLE_SECONDS = 8.0
POLL_MS = 2
THUMBNAILS = {
    FRONT.thumbnail_url: b"front-thumb",
    BACK.thumbnail_url: b"back-thumb",
}


class Heard:
    """Everything a runner passed on, in the order it arrived."""

    def __init__(self, runner: CoverRunner) -> None:
        self.offered: list = []
        self.previewed: list[tuple[int, object]] = []
        self.searched = 0
        self.kept: list[tuple[str, object]] = []
        runner.offered.connect(lambda found: self.offered.append(found))
        runner.previewed.connect(
            lambda position, picture: self.previewed.append((position, picture))
        )
        runner.searched.connect(self._on_searched)
        runner.kept.connect(lambda key, data: self.kept.append((key, data)))

    def _on_searched(self) -> None:
        """Count the searches that reported themselves finished."""
        self.searched += 1


def _runner(search, artwork=None) -> CoverRunner:
    """A runner over the real service, with the archive stood in for."""
    return CoverRunner(ChooseCover(search, artwork or FakeArtwork()))


def _settle(runner: CoverRunner, application: QApplication) -> None:
    """Let the errand finish and its answers be delivered.

    The work happens on another thread, so pumping this one is not enough: the
    other thread has to be given time to run before its answer can arrive.
    """
    deadline = time.monotonic() + SETTLE_SECONDS
    while time.monotonic() < deadline:
        application.processEvents()
        if not runner.running:
            application.processEvents()
            return
        QThread.msleep(POLL_MS)


@pytest.fixture
def application_events(application: QApplication) -> QApplication:
    """The one application, named for what these tests do with it."""
    return application


class TestASearch:
    def test_it_offers_what_came_back(self, application_events) -> None:
        runner = _runner(FakeSearch())
        heard = Heard(runner)
        runner.search(PLANETS)
        _settle(runner, application_events)
        runner.stop()
        assert heard.offered == [CoverOffer((FRONT, BACK))]

    def test_it_asks_the_archive_for_the_album_by_name(
        self, application_events
    ) -> None:
        search = FakeSearch()
        runner = _runner(search)
        runner.search(PLANETS)
        _settle(runner, application_events)
        runner.stop()
        assert search.searched == [("Holst", "The Planets")]

    def test_a_thumbnail_arrives_for_each_candidate_in_order(
        self, application_events
    ) -> None:
        runner = _runner(FakeSearch(pictures=THUMBNAILS))
        heard = Heard(runner)
        runner.search(PLANETS)
        _settle(runner, application_events)
        runner.stop()
        assert heard.previewed == [(0, b"front-thumb"), (1, b"back-thumb")]

    def test_a_picture_that_cannot_be_had_arrives_as_nothing(
        self, application_events
    ) -> None:
        runner = _runner(FakeSearch(pictures={FRONT.thumbnail_url: b"front-thumb"}))
        heard = Heard(runner)
        runner.search(PLANETS)
        _settle(runner, application_events)
        runner.stop()
        assert heard.previewed == [(0, b"front-thumb"), (1, None)]

    def test_it_says_when_it_has_finished(self, application_events) -> None:
        runner = _runner(FakeSearch())
        heard = Heard(runner)
        runner.search(PLANETS)
        _settle(runner, application_events)
        runner.stop()
        assert heard.searched == 1

    def test_an_archive_that_raises_offers_nothing_and_still_finishes(
        self, application_events
    ) -> None:
        runner = _runner(RaisingSearch())
        heard = Heard(runner)
        runner.search(PLANETS)
        _settle(runner, application_events)
        runner.stop()
        assert heard.offered == [CoverOffer()]
        assert heard.searched == 1


class TestCancellingBetweenRequests:
    """The flag is read at a boundary, which a worker run here can be watched at."""

    def test_a_cancelled_search_says_nothing_and_fetches_nothing(self) -> None:
        search = FakeSearch(pictures=THUMBNAILS)
        worker = SearchWorker(ChooseCover(search, FakeArtwork()), PLANETS)
        offered: list = []
        previewed: list[tuple] = []
        worker.offered.connect(offered.append)
        worker.previewed.connect(
            lambda position, picture: previewed.append((position, picture))
        )
        worker.cancel()
        worker.run()
        assert offered == []
        assert previewed == []
        assert search.fetched == []


class TestKeepingTheChosenPicture:
    def test_the_kept_copy_comes_back_under_the_album_key(
        self, application_events
    ) -> None:
        artwork = FakeArtwork()
        runner = _runner(FakeSearch(pictures={FRONT.image_url: b"full-size"}), artwork)
        heard = Heard(runner)
        runner.keep(ART_KEY, FRONT)
        _settle(runner, application_events)
        runner.stop()
        assert heard.kept == [(ART_KEY, KEPT)]
        assert artwork.kept == {ART_KEY: KEPT}

    def test_a_fetch_that_fails_keeps_nothing_and_says_so(
        self, application_events
    ) -> None:
        artwork = FakeArtwork()
        runner = _runner(FakeSearch(), artwork)
        heard = Heard(runner)
        runner.keep(ART_KEY, FRONT)
        _settle(runner, application_events)
        runner.stop()
        assert heard.kept == [(ART_KEY, None)]
        assert artwork.kept == {}

    def test_a_store_that_cannot_keep_reports_nothing_kept(
        self, application_events
    ) -> None:
        runner = _runner(
            FakeSearch(pictures={FRONT.image_url: b"full-size"}),
            FakeArtwork(keeps=False),
        )
        heard = Heard(runner)
        runner.keep(ART_KEY, FRONT)
        _settle(runner, application_events)
        runner.stop()
        assert heard.kept == [(ART_KEY, None)]

    def test_an_archive_that_raises_keeps_nothing(self, application_events) -> None:
        runner = _runner(RaisingSearch())
        heard = Heard(runner)
        runner.keep(ART_KEY, FRONT)
        _settle(runner, application_events)
        runner.stop()
        assert heard.kept == [(ART_KEY, None)]


class TestLettingGoOfASearchInFlight:
    """What cancelling actually promises, held against a search that is stuck."""

    def test_the_answer_to_a_search_let_go_of_is_dropped(
        self, application_events
    ) -> None:
        gate = threading.Event()
        runner = _runner(FakeSearch(pictures=THUMBNAILS, gate=gate))
        heard = Heard(runner)
        runner.search(PLANETS)
        # The search is inside its request, so this cannot stop it: the wait
        # times out and the thread is retired rather than forgotten.
        runner.cancel()
        assert runner.retired == 1
        assert not runner.running
        gate.set()
        deadline = time.monotonic() + SETTLE_SECONDS
        while time.monotonic() < deadline and runner.retired:
            application_events.processEvents()
            runner.stop()
            QThread.msleep(POLL_MS)
        application_events.processEvents()
        assert heard.offered == []
        assert heard.previewed == []
        assert heard.searched == 0

    def test_a_retired_thread_is_let_go_of_once_it_finishes(
        self, application_events
    ) -> None:
        gate = threading.Event()
        runner = _runner(FakeSearch(gate=gate))
        runner.search(PLANETS)
        runner.cancel()
        assert runner.retired == 1
        gate.set()
        deadline = time.monotonic() + SETTLE_SECONDS
        while time.monotonic() < deadline and runner.retired:
            application_events.processEvents()
            runner.stop()
            QThread.msleep(POLL_MS)
        assert runner.retired == 0
