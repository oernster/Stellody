"""The one module a discovery run opens a connection through, asked for real.

Against a service on the loopback address rather than a stand-in for one, since
what is being tested is what Qt makes of a status, a body and a silence.

**The request that can be given up on is the reason this module was rewritten.**
It used to block a thread inside `urlopen`, where nothing could reach it: a
listener who pressed stop waited out the request, up to the full timeout. So
the tests that matter most here are the two watching a request in flight be
abandoned; both assert how long that took rather than merely that it
happened.
"""

from __future__ import annotations

import time

import pytest
from PySide6.QtCore import QThread
from PySide6.QtNetwork import QNetworkAccessManager
from PySide6.QtWidgets import QApplication

from stellody.application.discovery_ports import (
    RateRefused,
    SourceFailed,
    SourceUnavailable,
)
from stellody.infrastructure.courtesy import USER_AGENT
from stellody.infrastructure.fetching import Fetcher
from tests.infrastructure.fetching_support import Service, nowhere

# What "at once" means when a request is abandoned. Generous by an order of
# magnitude against the measured figure, since the point is that nothing waits
# out a timeout rather than any particular millisecond.
PROMPTLY_S = 2.0
# Longer than two of the fetcher's give-up slices, so a request still wanted is
# asked about while it is in flight rather than only at the end of it.
SLOW_S = 0.6
# Short enough that the timeout arrives long before a held request would.
BRIEF_TIMEOUT_S = 0.2
# Long enough that no fetch here can reach it; the timeout is asked about by
# the one test that is about the timeout.
NO_TIMEOUT_S = 30.0
THREAD_LIMIT_MS = 5000
REFUSAL_CODES = [429, 503]
SERVICE_ERROR = 500


@pytest.fixture(scope="session")
def application() -> QApplication:
    """One real QApplication, since these are Qt objects. Qt is never mocked."""
    existing = QApplication.instance()
    return existing or QApplication([])


@pytest.fixture
def service(request: pytest.FixtureRequest):
    """A service configured by the test, closed however that test ends."""
    made = Service(**getattr(request, "param", {}))
    yield made
    made.close()


class OpenGate:
    """A gate that lets everything through at once and counts the asks."""

    def __init__(self) -> None:
        self.waits = 0

    def wait(self, wanted=None) -> bool:
        """Let it through, having noted that permission was sought."""
        self.waits += 1
        return True


class ShutGate:
    """A gate answering that nobody is waiting for this any more."""

    def wait(self, wanted=None) -> bool:
        """Refuse, the way a wait given up on part way through does."""
        return False


class Flipping:
    """Wanted for a while, then not. What pressing stop looks like."""

    def __init__(self, times: int) -> None:
        self._left = times

    def __call__(self) -> bool:
        """True until it has been asked often enough, False from then on."""
        self._left -= 1
        return self._left >= 0


def fetching(gate=None, timeout_s: float = NO_TIMEOUT_S, **manager) -> Fetcher:
    """A fetcher that waits for nothing it does not have to."""
    return Fetcher(gate=gate or OpenGate(), timeout_s=timeout_s, **manager)


class TestAskingAService:
    """An ordinary question with an ordinary answer."""

    @pytest.mark.parametrize("service", [{"body": {"ok": True}}], indirect=True)
    def test_it_waits_its_turn_and_names_the_application(
        self, application: QApplication, service: Service
    ) -> None:
        """The courtesies are applied here so no client can forget them."""
        gate = OpenGate()
        assert fetching(gate).json(service.address, {}) == {"ok": True}
        assert gate.waits == 1
        assert service.agents == [USER_AGENT]

    @pytest.mark.parametrize("service", [{"body": {}}], indirect=True)
    def test_it_builds_the_query_so_a_client_needs_no_networking(
        self, application: QApplication, service: Service
    ) -> None:
        """The reason the permitted-module list gained one name rather than two."""
        fetching().json(service.address, {"q": "a b", "fmt": "json"})
        assert service.asked == ["/ask?q=a+b&fmt=json"]

    @pytest.mark.parametrize(
        "service", [{"delay_s": SLOW_S, "body": []}], indirect=True
    )
    def test_a_slow_answer_still_wanted_is_waited_for(
        self, application: QApplication, service: Service
    ) -> None:
        """Asking whether anybody still wants it is not giving up on it.

        Slower than two of the give-up slices, so the question is put while the
        request is in flight and answered yes each time.
        """
        assert fetching().json(service.address, {}) == []


class TestGivingUpOnARequest:
    """The whole reason the module is written the way it is."""

    @pytest.mark.parametrize("service", [{"hangs": True}], indirect=True)
    def test_a_request_nobody_wants_any_more_is_dropped_at_once(
        self, application: QApplication, service: Service
    ) -> None:
        """Measured rather than asserted in the abstract: it is not waited out.

        The service accepts the connection then says nothing, which is the case
        that used to cost a listener the full twenty second timeout.
        """
        started = time.monotonic()
        with pytest.raises(SourceFailed, match="part way through"):
            fetching().json(service.address, {}, Flipping(1))
        assert time.monotonic() - started < PROMPTLY_S

    @pytest.mark.parametrize("service", [{"hangs": True}], indirect=True)
    def test_a_service_that_never_answers_is_given_up_on_anyway(
        self, application: QApplication, service: Service
    ) -> None:
        """The timeout is still the backstop for a run nobody has stopped."""
        started = time.monotonic()
        with pytest.raises(SourceFailed, match="part way through"):
            fetching(timeout_s=BRIEF_TIMEOUT_S).json(service.address, {})
        assert time.monotonic() - started < PROMPTLY_S

    def test_a_wait_given_up_on_is_never_asked_at_all(
        self, application: QApplication
    ) -> None:
        """A stop during the gap owed to a service ends it before the request."""
        with pytest.raises(SourceFailed, match="before it was asked"):
            fetching(ShutGate()).json(nowhere(), {})


class TestWhatCameBack:
    """An answer, a refusal or a failure, each meaning something different."""

    @pytest.mark.parametrize("code", REFUSAL_CODES)
    def test_a_refusal_is_asked_again_rather_than_reported(
        self, application: QApplication, code: int
    ) -> None:
        """The service asking for patience is not the service saying no."""
        service = Service(status=code, body={"error": "later"})
        try:
            with pytest.raises(RateRefused):
                fetching().json(service.address, {})
        finally:
            service.close()

    @pytest.mark.parametrize(
        "service", [{"status": SERVICE_ERROR, "body": {"error": "no"}}], indirect=True
    )
    def test_another_answer_is_that_artist_failing(
        self, application: QApplication, service: Service
    ) -> None:
        """One artist nobody could answer about, rather than the run ending."""
        with pytest.raises(SourceFailed, match=str(SERVICE_ERROR)):
            fetching().json(service.address, {})

    def test_nothing_answering_at_all_is_a_different_thing(
        self, application: QApplication
    ) -> None:
        """No connection means every later question fares the same way."""
        with pytest.raises(SourceUnavailable):
            fetching().json(nowhere(), {})

    @pytest.mark.parametrize("service", [{"text": "{"}], indirect=True)
    def test_an_answer_that_is_not_json_is_that_artist_failing(
        self, application: QApplication, service: Service
    ) -> None:
        """A service changing shape is one artist lost, not a run."""
        with pytest.raises(SourceFailed, match="could not be read"):
            fetching().json(service.address, {})

    def test_a_reply_answered_before_it_is_waited_on_is_not_waited_on(
        self, application: QApplication, tmp_path
    ) -> None:
        """A finished reply must not start a loop nothing will ever quit.

        Measured on 2026-09-07: a file address is the one kind Qt answers
        synchronously, so `get` hands back a reply that has already finished.
        Every service is asked over HTTP, where this cannot happen; the guard
        is here because a loop entered after the only thing that could quit it
        has already happened is a hang rather than an error.
        """
        missing = tmp_path / "nothing.json"
        with pytest.raises(SourceUnavailable):
            fetching().json(missing.as_uri(), {})


class Elsewhere(QThread):
    """Asks the fetcher which manager it would use, from another thread."""

    def __init__(self, fetcher: Fetcher) -> None:
        super().__init__()
        self._fetcher = fetcher
        self.answer: QNetworkAccessManager | None = None

    def run(self) -> None:
        """What the fetcher answers when the asking happens over here."""
        self.answer = self._fetcher._asking()


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
