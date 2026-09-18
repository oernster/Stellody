"""Where the fetcher's network manager lives; what a finished thread leaves.

Qt objects belong to the thread that made them, while a discovery run asks from
a thread of its own. These are the tests of that rule, split from the fetcher's
own suite so neither sits near the module length limit.
"""

from __future__ import annotations

import time

from PySide6.QtCore import QThread
from PySide6.QtNetwork import QNetworkAccessManager
from PySide6.QtWidgets import QApplication

from stellody.infrastructure.fetching import Fetcher
from tests.infrastructure.fetching_support import Service, fetching

# How long to give a socket to finish closing, in slices. The close is read by
# the server on its own thread, so it arrives shortly rather than at once.
SETTLING_SLICE_S = 0.05
SETTLING_SLICES = 60
THREAD_LIMIT_MS = 5000


class Elsewhere(QThread):
    """Asks the fetcher which manager it would use, from another thread."""

    def __init__(self, fetcher: Fetcher) -> None:
        super().__init__()
        self._fetcher = fetcher
        self.answer: QNetworkAccessManager | None = None

    def run(self) -> None:
        """What the fetcher answers when the asking happens over here."""
        self.answer = self._fetcher._asking()


class Fetching(QThread):
    """Makes a real request from another thread, as a run does."""

    def __init__(self, fetcher: Fetcher, address: str) -> None:
        super().__init__()
        self._fetcher = fetcher
        self._address = address
        self.answered: object = None
        self.manager: QNetworkAccessManager | None = None
        self.trouble = ""

    def run(self) -> None:
        """Ask once, then end, leaving whatever it opened behind.

        The manager is kept here as well, so this stands for the case where
        the fetcher letting go of it is not the last reference to it.
        """
        try:
            self.answered = self._fetcher.json(self._address, {})
            self.manager = self._fetcher._asking()
        except Exception as trouble:  # noqa: BLE001
            self.trouble = f"{type(trouble).__name__}: {trouble}"


def _settled(service: Service, application: QApplication) -> bool:
    """Whether the service has no connection open, given a moment to notice.

    A loop of slices rather than one sleep: a socket closes when the far end
    reads the close, which is its own thread's business rather than this
    one's, so the answer arrives shortly rather than immediately.
    """
    for _ in range(SETTLING_SLICES):
        application.processEvents()
        if service.open_connections == 0:
            return True
        time.sleep(SETTLING_SLICE_S)
    return False


class TestWhereTheManagerLives:
    """Qt objects belong to the thread that made them; a run has its own.

    Asked through the private method rather than through a fetch, because
    which manager was used has no other observable: two fetches from two
    threads both answer, whether or not the rule was honoured.
    """

    def test_one_thread_asking_twice_uses_the_manager_it_has(
        self, application: QApplication
    ) -> None:
        """Rebuilding it per request would throw away every kept connection."""
        fetcher = fetching(manager=QNetworkAccessManager())
        assert fetcher._asking() is fetcher._asking()

    def test_a_run_on_its_own_thread_gets_a_manager_of_its_own(
        self, application: QApplication
    ) -> None:
        """A manager used from a thread that did not make it is undefined."""
        fetcher = fetching(manager=QNetworkAccessManager())
        here = fetcher._asking()
        thread = Elsewhere(fetcher)
        thread.start()
        assert thread.wait(THREAD_LIMIT_MS), "the thread finished"
        assert thread.answer is not None
        assert thread.answer is not here

    def test_the_manager_is_let_go_when_its_thread_ends(
        self, application: QApplication
    ) -> None:
        """Measured from the diary on 2026-09-08, over two runs.

        A run keeps its connections open between requests, which the gap the
        terms ask for makes worth doing. Nothing closed them when the run
        ended, so idle sockets were left on a thread that had finished and Qt
        tore them down thirty seconds later with nobody home, saying
        `QIODevice::read (QSslSocket): device not open` once per host.

        Asserted on the manager rather than on the message, since the message
        is Qt's and arrives half a minute afterwards. What this holds is the
        thing that caused it: nothing of that thread's is still held once the
        thread has gone.
        """
        fetcher = fetching()
        thread = Elsewhere(fetcher)
        thread.start()
        assert thread.wait(THREAD_LIMIT_MS), "the thread finished"
        application.processEvents()
        assert thread.answer is not None, "it did build one over there"
        assert fetcher._held == {}, "and let go of it when that ended"

    def test_a_connection_left_open_is_closed_when_that_thread_ends(
        self, application: QApplication
    ) -> None:
        """The half of it that the reported message was actually about.

        A service that keeps a connection alive is what leaves an idle socket
        behind, so this asks one to, then watches the socket go when the
        thread that opened it ends. Against HTTP/1.0, which is what the rest
        of this file talks to, there is no connection to leave and nothing to
        see.
        """
        service = Service(body={"ok": True}, keeps_alive=True)
        try:
            thread = Fetching(fetching(), service.address)
            thread.start()
            assert thread.wait(THREAD_LIMIT_MS), "the thread finished"
            assert thread.answered == {"ok": True}, thread.trouble
            assert thread.manager is not None, "something else still holds it"
            assert _settled(
                service, application
            ), "the connection the run left open was closed with its thread"
        finally:
            service.close()
