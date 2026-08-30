"""Reading covers on a thread, one at a time, never asking twice.

The thread is real. Qt is never mocked, so what is stood in for is the reading
itself, which would otherwise open files and decode images.
"""

from __future__ import annotations

import time

import pytest
from PySide6.QtCore import QThread
from PySide6.QtWidgets import QApplication

from stellody.application.artwork import AlbumArtSources
from stellody.ui.art_worker import ArtRunner

FIRST = AlbumArtSources(key="aaaa", sidecars=("first.jpg",))
SECOND = AlbumArtSources(key="bbbb", sidecars=("second.jpg",))
COVER = b"cover-bytes"
SETTLE_SECONDS = 5.0
POLL_MS = 2


class SlowArt:
    """Reading, stood in for. It answers with the key it was asked about."""

    def __init__(self, answer: bytes | None = COVER) -> None:
        self.answer = answer
        self.asked: list[str] = []

    def reading(self, sources: AlbumArtSources) -> bytes | None:
        """Record the ask and answer at once."""
        self.asked.append(sources.key)
        return self.answer


class FailingArt:
    """Reading, gone wrong."""

    def reading(self, sources: AlbumArtSources) -> bytes | None:
        """Raise, as a decoder meeting something unreadable would."""
        raise RuntimeError("the file went away mid read")


@pytest.fixture
def arrived() -> list[tuple[str, object]]:
    """Every cover the runner passed on."""
    return []


def _runner(art, arrived) -> ArtRunner:
    """A runner reporting into a list."""
    made = ArtRunner(art)
    made.ready.connect(lambda key, cover: arrived.append((key, cover)))
    return made


def _settle(runner: ArtRunner, application: QApplication) -> None:
    """Let every queued read finish and every answer be delivered.

    The reading happens on another thread, so pumping this one is not enough:
    the other thread has to be given time to run before its answer can arrive.
    """
    deadline = time.monotonic() + SETTLE_SECONDS
    while time.monotonic() < deadline:
        application.processEvents()
        if not runner.running and not runner.pending:
            return
        QThread.msleep(POLL_MS)


def test_a_cover_reaches_the_window(application: QApplication, arrived) -> None:
    runner = _runner(SlowArt(), arrived)
    runner.want(FIRST)
    _settle(runner, application)
    assert arrived == [(FIRST.key, COVER)]
    runner.stop()


def test_an_album_is_never_asked_for_twice(application: QApplication, arrived) -> None:
    """Scrolling past an album again must not send anybody back to the disk."""
    art = SlowArt()
    runner = _runner(art, arrived)
    runner.want(FIRST)
    _settle(runner, application)
    runner.want(FIRST)
    _settle(runner, application)
    assert art.asked == [FIRST.key]
    runner.stop()


def test_an_album_with_no_cover_is_reported_as_having_none(
    application: QApplication, arrived
) -> None:
    """So the album can stop waiting and keep its placeholder."""
    runner = _runner(SlowArt(answer=None), arrived)
    runner.want(FIRST)
    _settle(runner, application)
    assert arrived == [(FIRST.key, None)]
    runner.stop()


def test_a_read_that_raises_says_nothing_rather_than_ending_the_run(
    application: QApplication, arrived
) -> None:
    """It runs on a thread with nobody above it to catch anything."""
    runner = _runner(FailingArt(), arrived)
    runner.want(FIRST)
    _settle(runner, application)
    assert arrived == [(FIRST.key, None)]
    runner.stop()


def test_several_albums_are_read_one_after_another(
    application: QApplication, arrived
) -> None:
    art = SlowArt()
    runner = _runner(art, arrived)
    runner.want(FIRST)
    runner.want(SECOND)
    _settle(runner, application)
    assert art.asked == [FIRST.key, SECOND.key]
    assert [key for key, _ in arrived] == [FIRST.key, SECOND.key]
    runner.stop()


def test_a_rescanned_library_may_be_asked_again(
    application: QApplication, arrived
) -> None:
    """A rescan can change what an album's cover is read from."""
    art = SlowArt()
    runner = _runner(art, arrived)
    runner.want(FIRST)
    _settle(runner, application)
    runner.forget()
    runner.want(FIRST)
    _settle(runner, application)
    assert art.asked == [FIRST.key, FIRST.key]
    runner.stop()


def test_stopping_is_safe_when_nothing_is_running(application: QApplication) -> None:
    """It runs on the way out, where a fault would be the last thing said."""
    runner = ArtRunner(SlowArt())
    runner.stop()
    runner.stop()
    assert not runner.running
