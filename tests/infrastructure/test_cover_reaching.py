"""Whether a cover search reached anything; whether it can reach it at all.

Three things measured on 2026-10-14 against the live services sit behind
these. The archive's listing names every picture over plain http. The archive
took up to 4.8 seconds to answer, so a one-second read slice gave up on about
half its requests. A search that gave up that way was then reported as an
album with no art.
"""

from __future__ import annotations

import json
import urllib.error

from cover_search_support import (
    ART,
    BOTH,
    LISTING_ANSWER,
    LISTING_HOST,
    SEARCH_ANSWER,
    SEARCH_HOST,
    client,
    encoded,
    refused_client,
)

from stellody.infrastructure.cover_search import (
    SEARCH_ATTEMPTS,
    SLICE_S,
    ArchiveCovers,
)
from stellody.ui.cover_worker import WAIT_MS

PLAIN_ART = ART.replace("https://", "http://", 1)
# The slowest answer either service gave on 2026-10-14 that did arrive.
SLOWEST_ANSWER_S = 4.8
MS_PER_S = 1000


def plain_listing() -> dict:
    """The listing as the archive answered on 2026-10-14: every address http."""
    return json.loads(json.dumps(LISTING_ANSWER).replace(ART, PLAIN_ART))


class TestTheSchemeTheListingNames:
    """The archive names its pictures over plain http, which the reach refuses.

    Left as written, every fetch was refused before it was made and every tile
    in the chooser stayed empty.
    """

    def plain(self) -> ArchiveCovers:
        # The picture first: the listing's prefix would answer for it too.
        return client(
            {
                SEARCH_HOST: encoded(SEARCH_ANSWER),
                f"{ART}/": b"a picture",
                LISTING_HOST: encoded(plain_listing()),
            }
        )[0]

    def test_a_plain_address_is_offered_over_https(self) -> None:
        offered = self.plain().search("Turin Brakes", "Ether Song").candidates
        assert offered[0].thumbnail_url == f"{ART}/38850137623-250.jpg"
        assert offered[0].image_url == f"{ART}/38850137623.jpg"

    def test_a_plain_address_can_be_fetched(self) -> None:
        found = self.plain()
        offered = found.search("Turin Brakes", "Ether Song").candidates
        assert found.fetch(offered[0].thumbnail_url) == b"a picture"
        assert found.fetch(offered[0].image_url) == b"a picture"

    def test_no_other_scheme_is_raised_to_https(self) -> None:
        """A `file:` address named in a listing stays one, so it stays refused."""
        listing = {
            "images": [
                {
                    "image": "file:///etc/passwd",
                    "thumbnails": {"250": "file:///etc/passwd"},
                }
            ]
        }
        found, _, _ = client(
            {SEARCH_HOST: encoded(SEARCH_ANSWER), LISTING_HOST: encoded(listing)}
        )
        offered = found.search("Turin Brakes", "Ether Song").candidates
        assert offered[0].thumbnail_url == "file:///etc/passwd"
        assert found.fetch(offered[0].thumbnail_url) is None


class TestASearchThatWasNeverAnswered:
    """A search that never came back says nothing about the album.

    Reporting it as "nothing came back for this album" tells a listener their
    album has no art anywhere, which the search never found out.
    """

    def test_a_search_that_timed_out_was_not_reached(self) -> None:
        found, _, _ = client({SEARCH_HOST: urllib.error.URLError("timed out")})
        offer = found.search("Turin Brakes", "Ether Song")
        assert offer.unreached
        assert not offer.refused
        assert offer.candidates == ()

    def test_a_search_answered_with_something_else_was_not_reached(self) -> None:
        found, _, _ = client({SEARCH_HOST: b"<html>down</html>"})
        assert found.search("Turin Brakes", "Ether Song").unreached

    def test_a_search_that_found_no_releases_was_reached(self) -> None:
        """An answer naming no releases is an answer: nothing was found."""
        found, _, _ = client({SEARCH_HOST: encoded({"releases": []})})
        offer = found.search("Turin Brakes", "Ether Song")
        assert not offer.unreached
        assert offer.candidates == ()

    def test_an_answered_search_was_reached(self) -> None:
        assert not client(BOTH)[0].search("Turin Brakes", "Ether Song").unreached

    def test_a_refusal_is_a_refusal_rather_than_unreached(self) -> None:
        found, _, _ = refused_client(SEARCH_ATTEMPTS)
        offer = found.search("Turin Brakes", "Ether Song")
        assert offer.refused
        assert not offer.unreached

    def test_a_listing_that_failed_leaves_the_search_reached(self) -> None:
        """A release is one of several; only the search itself is the answer."""
        found, _, _ = client(
            {
                SEARCH_HOST: encoded(SEARCH_ANSWER),
                LISTING_HOST: urllib.error.URLError("timed out"),
            }
        )
        assert not found.search("Turin Brakes", "Ether Song").unreached


class TestHowLongAReadMayTake:
    def test_a_slice_outlasts_the_slowest_answer_measured(self) -> None:
        """At one second, about half the requests on 2026-10-14 gave up."""
        assert SLICE_S > SLOWEST_ANSWER_S

    def test_a_cancelled_read_ends_inside_the_quit_wait(self) -> None:
        """A read notices a cancel within one slice; quitting waits this long.

        A slice longer than the wait leaves a thread still reading when the
        window lets go of it.
        """
        assert SLICE_S * MS_PER_S < WAIT_MS
