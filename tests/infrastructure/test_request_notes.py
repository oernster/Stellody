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
from stellody.infrastructure.fetching import Fetcher
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
