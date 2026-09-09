"""A pooled socket left standing longer than the host keeps it.

Reported by Oliver on 2026-09-09: a discovery run over an installed copy
produced no data. Measured the same day against MusicBrainz, asking one
question three times with the thirty second pause a run takes between passes
in between, the ask after each idle came back instantly with GOAWAY and
`RemoteHostClosedError`. The suite beside this already records the same idle
timeout from the other side: two sockets torn down at 29.9 seconds with
nobody home.

**What is asserted here is the connection, not the error.** The error itself
cannot be reproduced against a service on this machine. It arrives over HTTP/2
from a real host; Qt quietly asks again for itself when an HTTP/1.1 connection
is dropped, which is what the stdlib server here speaks. Measured
before this was written, by having that server close the connection on the
second, third and fourth asks: the fetcher saw an answer every time and no
error at all. So a fix written as a retry on that error would have been a fix
nothing here could see work.

The state is constrained instead, which this server can be asked about: a
connection idle longer than the limit is thrown away rather than asked down,
so the question is how many connections the service was asked to open. That
is a real socket, opened by real Qt, counted by a real server.
"""

from __future__ import annotations

import pytest
from PySide6.QtWidgets import QApplication
from test_fetching import NO_TIMEOUT_S, OpenGate

from stellody.infrastructure.fetching import Fetcher
from tests.infrastructure.fetching_support import Noting, Service

# The idle limit these run against. Small enough that a suite waits for
# nothing: the clock is handed in, so no test here sleeps at all.
BRIEF_IDLE_LIMIT_S = 10.0
# Two readings of the injected clock, one either side of the limit. Derived
# from it rather than written as numbers, so the limit cannot be changed here
# and leave a test asserting the opposite of what it says.
WITHIN_THE_LIMIT_S = BRIEF_IDLE_LIMIT_S / 2
PAST_THE_LIMIT_S = BRIEF_IDLE_LIMIT_S * 2


@pytest.fixture(scope="session")
def application() -> QApplication:
    """One real QApplication, since these are Qt objects. Qt is never mocked."""
    existing = QApplication.instance()
    return existing or QApplication([])


class Clock:
    """A clock that stands still until a test moves it on."""

    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        """The time this test says it is."""
        return self.now


def fetching(clock: Clock) -> Fetcher:
    """A fetcher reading that clock, with a briefer idle limit than a run's."""
    return Fetcher(
        gate=OpenGate(),
        timeout_s=NO_TIMEOUT_S,
        note=Noting(),
        idle_limit_s=BRIEF_IDLE_LIMIT_S,
        clock=clock,
    )


def test_a_connection_left_standing_too_long_is_not_asked_down(
    application: QApplication,
) -> None:
    """The defect itself: the ask after a long idle opens its own connection.

    Left as it was, that ask went down a socket the host had already let go
    of. It fell on the first artist of every pass, which is the same artist
    each time, so a run could go round twelve times and lose them every go.
    """
    clock = Clock()
    fetcher = fetching(clock)
    service = Service(body={"ok": True}, keeps_alive=True)
    try:
        assert fetcher.json(service.address, {}) == {"ok": True}
        clock.now += PAST_THE_LIMIT_S
        assert fetcher.json(service.address, {}) == {"ok": True}
        assert service.connections == 2, "the second ask opened its own"
    finally:
        service.close()


def test_a_connection_still_worth_believing_in_is_kept(
    application: QApplication,
) -> None:
    """The other half: this does not throw away a connection every time.

    Keeping one is the reason the gap the terms ask for is affordable at all,
    so a fix that opened a socket per question would be the opposite mistake.
    """
    clock = Clock()
    fetcher = fetching(clock)
    service = Service(body={"ok": True}, keeps_alive=True)
    try:
        assert fetcher.json(service.address, {}) == {"ok": True}
        clock.now += WITHIN_THE_LIMIT_S
        assert fetcher.json(service.address, {}) == {"ok": True}
        assert service.connections == 1, "both asks went down the one socket"
    finally:
        service.close()
