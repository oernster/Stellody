"""What a cancelled cover lookup stops doing, rather than what it stops saying.

Cancelling used to be a promise about the answer alone: the search finished at
its own pace and its answer was dropped. That left a thread inside a read for
up to thirty seconds after nobody wanted it, which is what ended the
application when the dialog holding it went away.

So the question travels: the worker asks it, the service passes it on and the
archive asks it between its slow parts and inside its reads. These tests are
about the archive end of that, since it is the end that does the waiting.
"""

from __future__ import annotations

import json
import urllib.error
from typing import Self

import pytest

from stellody.infrastructure.cover_search import (
    ART_URL,
    CHUNK_BYTES,
    REQUEST_GAP_S,
    SEARCH_ATTEMPTS,
    SEARCH_URL,
    SLEEP_SLICE_S,
    ArchiveCovers,
    Waiter,
)

PICTURE_URL = "https://example.invalid/front.jpg"


class Sleeper:
    """Every sleep the waiter actually took, in order."""

    def __init__(self) -> None:
        self.slept: list[float] = []

    def __call__(self, seconds: float) -> None:
        self.slept.append(seconds)


class Dwindling:
    """A body that arrives in pieces, counting how many were taken."""

    def __init__(self, pieces: int = 4) -> None:
        self.left = pieces
        self.reads = 0

    def read(self, _size: int | None = None) -> bytes:
        self.reads += 1
        if self.left <= 0:
            return b""
        self.left -= 1
        return b"x" * CHUNK_BYTES

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_: object) -> None:
        """Nothing to close: the pieces are made up on the spot."""


class Opening:
    """An opener handing back one prepared body, whatever is asked for."""

    def __init__(self, body) -> None:
        self.body = body
        self.asked: list[str] = []

    def __call__(self, request, timeout=None):
        self.asked.append(request.full_url)
        return self.body


def _stopping_after(turns: int):
    """A question that answers yes that many times and no from then on."""
    asked = {"turns": turns}

    def wanted() -> bool:
        if asked["turns"] <= 0:
            return False
        asked["turns"] -= 1
        return True

    return wanted


class TestTheWaiter:
    """The one place the slicing lives, so the one place it is pinned."""

    def test_a_wait_is_taken_in_slices(self) -> None:
        sleeper = Sleeper()
        assert Waiter(sleeper).hold(SLEEP_SLICE_S * 3, lambda: True)
        assert sleeper.slept == [SLEEP_SLICE_S] * 3

    def test_the_last_slice_is_only_what_is_left(self) -> None:
        """A gap that is not a whole number of slices is not overrun."""
        sleeper = Sleeper()
        Waiter(sleeper).hold(SLEEP_SLICE_S * 2.5, lambda: True)
        assert sleeper.slept == pytest.approx(
            [SLEEP_SLICE_S, SLEEP_SLICE_S, SLEEP_SLICE_S * 0.5]
        )

    def test_it_is_given_up_part_way_through(self) -> None:
        sleeper = Sleeper()
        assert not Waiter(sleeper).hold(SLEEP_SLICE_S * 10, _stopping_after(2))
        assert len(sleeper.slept) == 2, "it stopped rather than seeing it out"

    def test_a_wait_nobody_wants_at_all_is_never_started(self) -> None:
        sleeper = Sleeper()
        assert not Waiter(sleeper).hold(REQUEST_GAP_S, lambda: False)
        assert sleeper.slept == []


class TestAReadThatIsGivenUp:
    def test_it_stops_between_pieces(self) -> None:
        """Rather than at the end of a picture nobody is going to see."""
        body = Dwindling(pieces=10)
        found = ArchiveCovers(opener=Opening(body), waiter=Waiter(Sleeper()))
        assert found.fetch(PICTURE_URL, _stopping_after(2)) is None
        assert body.reads == 2, "it read two pieces and walked away"

    def test_a_picture_nobody_wants_is_not_read_at_all(self) -> None:
        body = Dwindling()
        found = ArchiveCovers(opener=Opening(body), waiter=Waiter(Sleeper()))
        assert found.fetch(PICTURE_URL, lambda: False) is None
        assert body.reads == 0

    def test_a_picture_still_wanted_comes_back_whole(self) -> None:
        """The pieces are the same picture: nothing is lost by taking it in
        parts, which is the thing a chunked read has to prove."""
        body = Dwindling(pieces=3)
        found = ArchiveCovers(opener=Opening(body), waiter=Waiter(Sleeper()))
        assert found.fetch(PICTURE_URL, lambda: True) == b"x" * CHUNK_BYTES * 3


class Refusing:
    """An opener that always refuses, so the backoff is exercised."""

    def __init__(self) -> None:
        self.asked: list[str] = []

    def __call__(self, request, timeout=None):
        self.asked.append(request.full_url)
        raise urllib.error.HTTPError(request.full_url, 503, "BUSY", {}, None)


class TestASearchGivenUpBetweenAsks:
    def test_it_stops_asking_rather_than_waiting_out_the_backoff(self) -> None:
        opener = Refusing()
        sleeper = Sleeper()
        found = ArchiveCovers(opener=opener, waiter=Waiter(sleeper))
        # Wanted for the first ask and its gate, then not: what a listener
        # closing the chooser one second in looks like from down here.
        offer = found.search("Turin Brakes", "Ether Song", _stopping_after(2))
        assert offer.candidates == ()
        assert len(opener.asked) == 1, f"asked {len(opener.asked)} times"
        assert len(sleeper.slept) < SEARCH_ATTEMPTS, "it sat through the backoff"

    def test_the_listings_are_not_walked_once_nobody_is_waiting(self) -> None:
        """The search answers with four releases and each is a request of its
        own. Held against the same walk with nobody cancelling, so a pass
        cannot come from the search having failed for another reason."""
        opener = Listing()
        found = ArchiveCovers(opener=opener, waiter=Waiter(Sleeper()))
        found.search("Holst", "The Planets", _stopping_after(3))
        assert opener.listings == [], "a listing went out after the cancel"

        opener = Listing()
        found = ArchiveCovers(opener=opener, waiter=Waiter(Sleeper()))
        found.search("Holst", "The Planets", lambda: True)
        assert len(opener.listings) == RELEASES, "the walk itself is not broken"


RELEASES = 4


class Stream:
    """A body handed over in one piece, then nothing."""

    def __init__(self, data: bytes) -> None:
        self.data = data
        self.given = False

    def read(self, _size: int | None = None) -> bytes:
        if self.given:
            return b""
        self.given = True
        return self.data

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_: object) -> None:
        """Nothing to close: the bytes were made up on the spot."""


class Listing:
    """An archive answering a search with releases, then a listing each."""

    def __init__(self) -> None:
        self.asked: list[str] = []
        self.answer = json.dumps(
            {
                "releases": [
                    {"id": str(n), "title": "The Planets"} for n in range(RELEASES)
                ]
            }
        ).encode("utf-8")

    @property
    def listings(self) -> list[str]:
        """The requests that went to the archive rather than to the search."""
        return [url for url in self.asked if url.startswith(ART_URL)]

    def __call__(self, request, timeout=None):
        self.asked.append(request.full_url)
        if request.full_url.startswith(SEARCH_URL):
            return Stream(self.answer)
        return Stream(b"{}")
