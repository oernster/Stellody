"""One Stellody at a time, over the channel to the copy already running.

Measured on a machine where the window had been closed to the notification
area: the window existed but was hidden, so it had no button on the taskbar;
clicking the pinned shortcut started a second copy rather than showing the one
already there.

Nothing here is Windows only. A system semaphore, a shared memory segment and
a local socket are the same three objects on Windows, Linux and macOS.
"""

from __future__ import annotations

import pytest
from PySide6.QtNetwork import QLocalServer, QLocalSocket
from PySide6.QtWidgets import QApplication

from stellody.infrastructure.instance import SingleInstance

GUARD = "Stellody.tests.guard"
CLAIM = "Stellody.tests.claim"
CHANNEL = "Stellody.tests.activation"


@pytest.fixture(scope="session")
def application() -> QApplication:
    """One real QApplication, since these are Qt objects. Qt is never mocked."""
    existing = QApplication.instance()
    return existing or QApplication([])


@pytest.fixture
def copies(application: QApplication):
    """Two copies of the application, as two launches would be."""
    made = [SingleInstance(GUARD, CLAIM, CHANNEL) for _ in range(2)]
    yield made
    for copy in made:
        copy.release()
    QLocalServer.removeServer(CHANNEL)


def test_the_first_copy_takes_the_claim_and_a_second_is_refused(copies) -> None:
    first, second = copies
    assert first.take() is True
    assert second.take() is False, "a second copy is not the one that runs"


def test_a_second_copy_asks_the_first_to_come_forward(
    application: QApplication, copies
) -> None:
    """The whole point: the click reaches the window nobody can see."""
    first, second = copies
    first.take()
    asked: list[str] = []
    assert first.listen(lambda: asked.append("came forward")) is True
    assert second.ask() is True, "somebody answered"
    application.processEvents()
    assert asked == ["came forward"]


def _knock(word: bytes | None) -> None:
    """Open the channel as any process on the machine may, saying `word`."""
    caller = QLocalSocket()
    caller.connectToServer(CHANNEL)
    assert caller.waitForConnected(1000), "the channel accepted the connection"
    if word is not None:
        caller.write(word)
        caller.flush()
        caller.waitForBytesWritten(1000)
    caller.disconnectFromServer()


@pytest.mark.parametrize("word", [None, b"", b"who is there"])
def test_a_caller_that_never_asks_leaves_the_window_where_it_is(
    application: QApplication, copies, word: bytes | None
) -> None:
    """The bug this guards: connecting alone used to be taken as the ask.

    Anything enumerating named pipes opens this one. Measured before the
    guard existed: a connection carrying nothing at all brought the window
    up out of the notification area.
    """
    first, _ = copies
    first.take()
    asked: list[str] = []
    assert first.listen(lambda: asked.append("came forward")) is True
    _knock(word)
    application.processEvents()
    assert asked == [], "nobody asked, so nothing came forward"


def test_asking_where_nothing_listens_says_so_rather_than_waiting(copies) -> None:
    """A copy that cannot be reached must not hang on somebody's click."""
    first, second = copies
    first.take()
    QLocalServer.removeServer(CHANNEL)
    assert second.ask() is False


def test_releasing_lets_the_next_launch_be_the_one_that_runs(copies) -> None:
    """However a copy ends, the next one must not be locked out."""
    first, second = copies
    assert first.take() is True
    first.release()
    assert second.take() is True


def test_releasing_is_safe_whether_or_not_the_claim_was_taken(copies) -> None:
    """It runs on the way out, where a fault would be the last thing said."""
    first, _ = copies
    first.release()
    first.release()


def test_ownership_is_the_claim_rather_than_the_channel(
    application: QApplication, copies
) -> None:
    """Which is why the two are separate objects.

    Measured on Windows: a second listener binds the same pipe name quite
    happily, so a channel that answers proves nothing about who owns the
    application. On Unix the opposite trap waits, a socket left behind by a
    copy the system ended, which is why listen clears the name first. That
    path cannot be exercised here and is not claimed to be.
    """
    first, second = copies
    assert first.take() is True
    assert first.listen(lambda: None) is True
    assert second.listen(lambda: None) is True, "the channel is not the claim"
    assert second.take() is False, "the claim is"
