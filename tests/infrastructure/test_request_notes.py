"""What a request writes down about itself once it has ended.

Reported on 2026-09-08: `QIODevice::read (QNetworkReplyHttpImpl): device not
open`, written on the discovery run's own thread; in three runs out of three,
within 25 milliseconds of the run ending. Two explanations were tested
and both were disproved. Qt's own messages already reach the diary carrying the
thread that wrote them; what was missing was which request each one sat beside.

So this is an instrument rather than logging. What it has to carry is exactly
that: the address asked, what the request came to and how long it took.
A line missing any of the three would leave the next sighting as unplaceable as
the last one.
"""

from __future__ import annotations

import pytest
from PySide6.QtWidgets import QApplication

from stellody.application.discovery_ports import RateRefused
from stellody.infrastructure.fetching import SAID_LIMIT, Fetcher
from tests.infrastructure.fetching_support import Noting, Service

REFUSAL_CODE = 503
NO_TIMEOUT_S = 30.0


class OpenGate:
    """A gate that lets everything through at once."""

    def wait(self, wanted=None) -> bool:
        """Let it through."""
        return True


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


def _fetching(notes: Noting) -> Fetcher:
    """A fetcher writing to this recorder and waiting for nothing."""
    return Fetcher(gate=OpenGate(), timeout_s=NO_TIMEOUT_S, note=notes)


@pytest.mark.parametrize("service", [{"body": {"ok": True}}], indirect=True)
def test_an_answered_request_says_so(
    application: QApplication, service: Service
) -> None:
    """One line per request, whatever the request came to."""
    notes = Noting()
    assert _fetching(notes).json(service.address, {"q": "a"}) == {"ok": True}
    assert len(notes.lines) == 1
    assert "answered" in notes.lines[0]


@pytest.mark.parametrize("service", [{"body": {"ok": True}}], indirect=True)
def test_the_line_names_the_request_it_belongs_to(
    application: QApplication, service: Service
) -> None:
    """Without the address a line cannot be matched to anything."""
    notes = Noting()
    _fetching(notes).json(service.address, {"q": "a b"})
    assert "q=a+b" in notes.lines[0]


@pytest.mark.parametrize("service", [{"body": {"ok": True}}], indirect=True)
def test_the_line_says_how_long_it_took(
    application: QApplication, service: Service
) -> None:
    """A warning is placed by time, so a line without a duration places it
    only against the moment the request ended rather than against the whole of
    it."""
    notes = Noting()
    _fetching(notes).json(service.address, {})
    assert notes.lines[0].endswith("ms")


@pytest.mark.parametrize(
    "service", [{"status": REFUSAL_CODE, "body": {"error": "later"}}], indirect=True
)
def test_a_request_that_ended_badly_is_written_down_too(
    application: QApplication, service: Service
) -> None:
    """The interesting request is the one that did not answer, so a note only
    on the way out would miss every case worth reading."""
    notes = Noting()
    with pytest.raises(RateRefused):
        _fetching(notes).json(service.address, {})
    assert len(notes.lines) == 1
    assert "RateRefused" in notes.lines[0]


class TestWhatTheServiceSaidAboutIt:
    """A refusal in the service's own words.

    Measured on 2026-09-08: 21 refusals in one run of 27 requests, each
    arriving in about 30 milliseconds, with nothing to say whether the service
    was asking for a slower pace or reporting that it was not there. Those are
    different faults with different cures, so the words matter.
    """

    @pytest.mark.parametrize(
        "service",
        [{"status": REFUSAL_CODE, "body": {"error": "Slow down, you."}}],
        indirect=True,
    )
    def test_it_carries_the_reason_the_service_gave(
        self, application: QApplication, service: Service
    ) -> None:
        notes = Noting()
        with pytest.raises(RateRefused) as refusal:
            _fetching(notes).json(service.address, {})
        assert "Slow down, you." in str(refusal.value)
        assert str(REFUSAL_CODE) in str(refusal.value), "and which refusal it was"

    @pytest.mark.parametrize(
        "service",
        [{"status": REFUSAL_CODE, "text": "<html>go\n  away</html>"}],
        indirect=True,
    )
    def test_a_body_that_is_not_json_is_carried_as_it_reads(
        self, application: QApplication, service: Service
    ) -> None:
        """A service behind a proxy answers in the proxy's words, not its own."""
        notes = Noting()
        with pytest.raises(RateRefused) as refusal:
            _fetching(notes).json(service.address, {})
        assert "<html>go away</html>" in str(refusal.value), "on one line"

    @pytest.mark.parametrize(
        "service", [{"status": REFUSAL_CODE, "body": ["no"]}], indirect=True
    )
    def test_json_that_names_no_reason_is_carried_whole(
        self, application: QApplication, service: Service
    ) -> None:
        notes = Noting()
        with pytest.raises(RateRefused) as refusal:
            _fetching(notes).json(service.address, {})
        assert '["no"]' in str(refusal.value)

    @pytest.mark.parametrize(
        "service",
        [{"status": REFUSAL_CODE, "body": {"error": "x" * (SAID_LIMIT * 2)}}],
        indirect=True,
    )
    def test_a_body_the_size_of_a_page_is_cut_short(
        self, application: QApplication, service: Service
    ) -> None:
        """A note is read beside other notes, so one line stays one line."""
        notes = Noting()
        with pytest.raises(RateRefused) as refusal:
            _fetching(notes).json(service.address, {})
        assert "x" * SAID_LIMIT in str(refusal.value)
        assert "x" * (SAID_LIMIT + 1) not in str(refusal.value)
