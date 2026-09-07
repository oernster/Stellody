"""Asking what one candidate artist released, at the moment somebody asks.

Driven against a hand-written catalogue, so what is tested is the rule about
which releases are kept and the patience applied to a refusal, rather than
anything a network did.
"""

from __future__ import annotations

import pytest
from discovery_support import Waits

from stellody.application.asking import RETRY_ATTEMPTS, RETRY_PAUSE_SECONDS
from stellody.application.choosing_covers import Wanted, always_wanted
from stellody.application.discovery_ports import (
    RateRefused,
    RunCancelled,
    SourceFailed,
    SourceUnavailable,
)
from stellody.application.expanding import Expansion, never_stopped
from stellody.domain.discovery import ReleaseGroup
from stellody.domain.matching import ReleaseKind

WOLF = "wolf-id"


class Releasing:
    """A catalogue answering with one prepared discography."""

    def __init__(
        self,
        released: tuple[ReleaseGroup, ...] = (),
        raises: Exception | None = None,
        refusals: int = 0,
    ) -> None:
        self._released = released
        self._raises = raises
        self._refusals = refusals
        self.asked: list[str] = []
        self.wanted: list[Wanted] = []

    def albums_of(
        self, identifier: str, wanted: Wanted = always_wanted
    ) -> tuple[ReleaseGroup, ...]:
        """Answer as this fake was told, recording what it was asked."""
        self.asked.append(identifier)
        self.wanted.append(wanted)
        if self._refusals:
            self._refusals -= 1
            raise RateRefused("asked to wait")
        if self._raises is not None:
            raise self._raises
        return self._released


def expanding(catalogue: Releasing) -> tuple[Expansion, Waits]:
    """An expansion wired to this catalogue, waiting for nothing."""
    waits = Waits()
    return Expansion(catalogue=catalogue, pause=waits), waits


def test_everything_that_artist_made_is_offered() -> None:
    """FR-D31: nothing is held by them, so nothing is dropped as held."""
    catalogue = Releasing(
        (
            ReleaseGroup(title="Moanin", kinds=(), genres=("Blues",)),
            ReleaseGroup(title="Live At The Cafe", kinds=(ReleaseKind.LIVE,)),
        )
    )
    expansion, _ = expanding(catalogue)
    found = expansion.releases_of(WOLF)
    assert [group.title for group in found] == ["Moanin", "Live At The Cafe"]
    assert catalogue.asked == [WOLF]


def test_a_hits_package_is_still_noise() -> None:
    """The one rule that survives the move to a candidate artist."""
    catalogue = Releasing(
        (
            ReleaseGroup(title="The Very Best Of", kinds=(ReleaseKind.COMPILATION,)),
            ReleaseGroup(title="A Record", kinds=()),
        )
    )
    expansion, _ = expanding(catalogue)
    assert [group.title for group in expansion.releases_of(WOLF)] == ["A Record"]


def test_an_artist_who_released_nothing_offers_nothing() -> None:
    """A catalogue answering with an empty list is not an error."""
    expansion, _ = expanding(Releasing(()))
    assert expansion.releases_of(WOLF) == ()


def test_a_refusal_is_waited_out_rather_than_reported() -> None:
    """Measured at 6 refusals in 10 asks; giving up once would mostly fail."""
    catalogue = Releasing((ReleaseGroup(title="A Record"),), refusals=1)
    expansion, waits = expanding(catalogue)
    assert [group.title for group in expansion.releases_of(WOLF)] == ["A Record"]
    assert catalogue.asked == [WOLF, WOLF], "it asked again"
    assert sum(waits.waited) == pytest.approx(RETRY_PAUSE_SECONDS)


def test_a_source_refusing_every_time_is_that_artist_failing() -> None:
    """FR-D32: the caller is told, rather than the list being lost."""
    expansion, _ = expanding(Releasing(refusals=RETRY_ATTEMPTS))
    with pytest.raises(SourceFailed):
        expansion.releases_of(WOLF)


def test_a_source_that_cannot_be_reached_says_so() -> None:
    """Not caught here: what to say about it belongs to whoever asked."""
    expansion, _ = expanding(Releasing(raises=SourceUnavailable("no route")))
    with pytest.raises(SourceUnavailable):
        expansion.releases_of(WOLF)


def test_a_caller_with_nothing_to_stop_is_the_ordinary_case() -> None:
    """One expansion is one request, so most callers have nothing to cancel."""
    assert never_stopped() is False


def test_a_window_closing_mid_answer_stops_the_ask() -> None:
    """It is still offered, since a stop is a stop however small the work."""
    catalogue = Releasing((ReleaseGroup(title="A Record"),))
    expansion, _ = expanding(catalogue)
    with pytest.raises(RunCancelled):
        expansion.releases_of(WOLF, cancelled=lambda: True)
    assert catalogue.asked == [], "it never asked at all"


def test_the_question_carries_whether_it_is_still_wanted() -> None:
    """The predicate goes down with the request, as it does for a run."""
    catalogue = Releasing((ReleaseGroup(title="A Record"),))
    expansion, _ = expanding(catalogue)
    expansion.releases_of(WOLF)
    handed = catalogue.wanted[0]
    assert handed() is True, "still wanted while nobody has stopped anything"
