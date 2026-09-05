"""Reading MusicBrainz and the Cover Art Archive, without reaching either.

The JSON below is not invented. It is the shape those two services actually
answered with on 2026-08-30, cut down to the fields this client reads. A test
written against a remembered API is a test of the memory.

No connection is opened here. The opener is handed in, which is also how the
gate is: waiting a real second between requests would make this suite a minute
longer for nothing.
"""

from __future__ import annotations

import json
import urllib.error
from io import BytesIO

from stellody.infrastructure.cover_search import (
    CONTACT,
    RELEASE_LIMIT,
    SEARCH_ATTEMPTS,
    USER_AGENT,
    ArchiveCovers,
)

MBID = "69249908-12ef-4eae-be48-46acf1354837"
ART = f"https://coverartarchive.org/release/{MBID}"

SEARCH_ANSWER = {
    "count": 8,
    "releases": [
        {
            "id": MBID,
            "title": "Ether Song",
            "date": "2003-11-17",
            "country": "GB",
            "track-count": 15,
        }
    ],
}

LISTING_ANSWER = {
    "images": [
        {
            "approved": True,
            "back": False,
            "front": True,
            "id": "38850137623",
            "image": f"{ART}/38850137623.jpg",
            "thumbnails": {
                "250": f"{ART}/38850137623-250.jpg",
                "500": f"{ART}/38850137623-500.jpg",
                "1200": f"{ART}/38850137623-1200.jpg",
                "large": f"{ART}/38850137623-500.jpg",
                "small": f"{ART}/38850137623-250.jpg",
            },
            "types": ["Front"],
        },
        {
            "back": True,
            "front": False,
            "id": "38850137624",
            "image": f"{ART}/38850137624.jpg",
            "thumbnails": {"250": f"{ART}/38850137624-250.jpg"},
            "types": ["Back"],
        },
    ]
}


class NoWait:
    """A gate that lets everything through, so the suite does not wait."""

    def __init__(self) -> None:
        self.waits = 0

    def wait(self, wanted=lambda: True) -> bool:
        """Count the request and let it go, unless nobody wants it."""
        self.waits += 1
        return wanted()


class Answering:
    """An opener answering canned bytes, remembering what it was asked."""

    def __init__(self, answers: dict) -> None:
        self.answers = answers
        self.asked: list[str] = []
        self.headers: list[dict] = []

    def __call__(self, request, timeout=None):
        """Answer this request; raise the error it was told to raise."""
        self.asked.append(request.full_url)
        self.headers.append(dict(request.header_items()))
        for prefix, answer in self.answers.items():
            if request.full_url.startswith(prefix):
                if isinstance(answer, Exception):
                    raise answer
                return BytesIO(answer)
        raise urllib.error.HTTPError(request.full_url, 404, "NOT FOUND", {}, None)


def encoded(value: dict) -> bytes:
    """One canned JSON answer as bytes."""
    return json.dumps(value).encode("utf-8")


class Pauses:
    """The backoff, recorded rather than waited through."""

    def __init__(self) -> None:
        self.slept: list[float] = []

    def hold(self, seconds: float, wanted=lambda: True) -> bool:
        """Note the whole pause and return at once.

        The gap asked for rather than the slices the real waiter takes it in:
        what the terms ask for is the thing worth pinning.
        """
        self.slept.append(seconds)
        return wanted()


def client(answers: dict) -> tuple[ArchiveCovers, Answering, NoWait]:
    """A client over a canned opener and a gate that never waits."""
    opener = Answering(answers)
    gate = NoWait()
    return ArchiveCovers(gate=gate, opener=opener, waiter=Pauses()), opener, gate


BOTH = {
    "https://musicbrainz.org": encoded(SEARCH_ANSWER),
    "https://coverartarchive.org/release/": encoded(LISTING_ANSWER),
}


class TestWhatTheSearchAsksFor:
    def test_both_terms_go_in_as_quoted_phrases(self) -> None:
        found, opener, _ = client(BOTH)
        found.search("Turin Brakes", "Ether Song")
        asked = opener.asked[0]
        assert "artist%3A%22Turin+Brakes%22" in asked
        assert "release%3A%22Ether+Song%22" in asked
        assert f"limit={RELEASE_LIMIT}" in asked

    def test_the_request_names_the_application(self) -> None:
        """The terms ask for it. A service that cannot tell who is asking
        cannot do anything but refuse everyone."""
        found, opener, _ = client(BOTH)
        found.search("Turin Brakes", "Ether Song")
        agent = opener.headers[0].get("User-agent")
        assert agent == USER_AGENT
        assert "Stellody" in agent
        assert CONTACT in agent, "and how to reach whoever is asking"

    def test_a_quote_in_a_title_cannot_break_the_phrase(self) -> None:
        """A Lucene phrase ended early searches for something else entirely."""
        found, opener, _ = client(BOTH)
        found.search('Guns "N" Roses', "Use Your Illusion")
        assert "%22" in opener.asked[0]
        assert opener.asked[0].count("%22") == 4, "two phrases, four quotes"

    def test_every_request_waits_its_turn(self) -> None:
        found, _, gate = client(BOTH)
        found.search("Turin Brakes", "Ether Song")
        assert gate.waits == 2, "one for the search, one for the release"


class TestWhatComesBack:
    def test_the_pictures_of_a_release_are_offered(self) -> None:
        found, _, _ = client(BOTH)
        offered = found.search("Turin Brakes", "Ether Song").candidates
        assert len(offered) == 2
        assert offered[0].is_front is True
        assert offered[1].is_front is False

    def test_the_largest_thumbnail_is_what_a_candidate_claims(self) -> None:
        """The listing never carries the size of the original, measured."""
        offered = client(BOTH)[0].search("Turin Brakes", "Ether Song").candidates
        assert offered[0].largest_px == 1200
        assert offered[1].largest_px == 250

    def test_the_smallest_thumbnail_is_what_the_chooser_draws(self) -> None:
        offered = client(BOTH)[0].search("Turin Brakes", "Ether Song").candidates
        assert offered[0].thumbnail_url.endswith("-250.jpg")
        assert offered[0].image_url.endswith("38850137623.jpg")

    def test_a_release_is_named_by_its_title_date_and_country(self) -> None:
        offered = client(BOTH)[0].search("Turin Brakes", "Ether Song").candidates
        assert offered[0].release == "Ether Song  2003-11-17  GB"


class TestWhenThereIsNothingToBeHad:
    def test_a_release_with_no_art_is_an_answer_not_a_failure(self) -> None:
        """The archive answers 404 for a release nobody has photographed."""
        found, _, _ = client({"https://musicbrainz.org": encoded(SEARCH_ANSWER)})
        assert found.search("Turin Brakes", "Ether Song").candidates == ()

    def test_a_search_that_cannot_be_made_offers_nothing(self) -> None:
        found, _, _ = client(
            {"https://musicbrainz.org": urllib.error.URLError("no route")}
        )
        assert found.search("Turin Brakes", "Ether Song").candidates == ()

    def test_an_answer_that_is_not_json_offers_nothing(self) -> None:
        found, _, _ = client({"https://musicbrainz.org": b"<html>down</html>"})
        assert found.search("Turin Brakes", "Ether Song").candidates == ()

    def test_an_answer_that_is_json_but_not_an_object_offers_nothing(self) -> None:
        found, _, _ = client({"https://musicbrainz.org": b"[1, 2, 3]"})
        assert found.search("Turin Brakes", "Ether Song").candidates == ()

    def test_a_release_with_no_identifier_is_passed_over(self) -> None:
        answer = {"releases": [{"title": "Ether Song"}]}
        found, _, _ = client({"https://musicbrainz.org": encoded(answer)})
        assert found.search("Turin Brakes", "Ether Song").candidates == ()

    def test_an_image_with_nowhere_to_point_is_passed_over(self) -> None:
        listing = {"images": [{"front": True, "thumbnails": {}}, {"image": ""}]}
        found, _, _ = client(
            {
                "https://musicbrainz.org": encoded(SEARCH_ANSWER),
                "https://coverartarchive.org/release/": encoded(listing),
            }
        )
        assert found.search("Turin Brakes", "Ether Song").candidates == ()


class TestFetchingAPicture:
    def test_the_bytes_come_back(self) -> None:
        found, _, _ = client({ART: b"a picture"})
        assert found.fetch(f"{ART}/38850137623-250.jpg") == b"a picture"

    def test_a_picture_that_cannot_be_had_is_nothing(self) -> None:
        found, _, _ = client({})
        assert found.fetch(f"{ART}/gone.jpg") is None

    def test_fetching_does_not_wait_its_turn(self) -> None:
        """A grid of a dozen at a second each opens a dozen seconds late."""
        found, _, gate = client({ART: b"a picture"})
        found.fetch(f"{ART}/one.jpg")
        found.fetch(f"{ART}/two.jpg")
        assert gate.waits == 0


class Refusing:
    """An opener refusing a set number of times before it answers."""

    def __init__(self, refusals: int, answers: dict, code: int = 503) -> None:
        self.refusals = refusals
        self.answers = answers
        self.code = code
        self.asked = 0

    def __call__(self, request, timeout=None):
        """Refuse while there are refusals left, then answer normally."""
        self.asked += 1
        if self.refusals > 0:
            self.refusals -= 1
            raise urllib.error.HTTPError(
                request.full_url, self.code, "SERVICE UNAVAILABLE", {}, None
            )
        for prefix, answer in self.answers.items():
            if request.full_url.startswith(prefix):
                return BytesIO(answer)
        raise urllib.error.HTTPError(request.full_url, 404, "NOT FOUND", {}, None)


def _refused_client(refusals: int, code: int = 503):
    """A client whose search host refuses that many times first."""
    opener = Refusing(refusals, BOTH, code)
    pauses = Pauses()
    return ArchiveCovers(gate=NoWait(), opener=opener, waiter=pauses), opener, pauses


class TestARefusalIsAskedAgainAbout:
    """Measured 2026-08-31: MusicBrainz refused 6 of 10 asks at 1.1s spacing.

    So one ask is not a search. These pin that a refusal is retried, that the
    pause between asks grows, then that what survives every ask is reported as
    a refusal rather than as an album with no art.
    """

    def test_a_search_refused_once_is_asked_again_and_answered(self) -> None:
        found, opener, _ = _refused_client(1)
        offer = found.search("Turin Brakes", "Ether Song")
        assert offer.candidates
        assert not offer.refused
        assert opener.asked > 1

    def test_a_search_refused_every_time_says_it_was_refused(self) -> None:
        found, opener, _ = _refused_client(SEARCH_ATTEMPTS)
        offer = found.search("Turin Brakes", "Ether Song")
        assert offer.refused
        assert offer.candidates == ()
        assert opener.asked == SEARCH_ATTEMPTS

    def test_too_many_requests_is_a_refusal_too(self) -> None:
        found, opener, _ = _refused_client(1, code=429)
        assert found.search("Turin Brakes", "Ether Song").candidates
        assert opener.asked > 1

    def test_the_pause_between_asks_grows(self) -> None:
        found, _, pauses = _refused_client(SEARCH_ATTEMPTS)
        found.search("Turin Brakes", "Ether Song")
        assert pauses.slept == sorted(pauses.slept)
        assert len(set(pauses.slept)) == len(pauses.slept)

    def test_an_ordinary_failure_is_not_asked_again(self) -> None:
        """A 404 is an answer. Asking again would only wait to hear it twice."""
        found, opener, _ = client({})
        offer = found.search("Turin Brakes", "Ether Song")
        assert offer.candidates == ()
        assert not offer.refused
        assert len(opener.asked) == 1

    def test_a_listing_that_is_refused_leaves_the_search_answered(self) -> None:
        """A release is one of several; only the search itself is the answer."""
        opener = Answering({"https://musicbrainz.org": encoded(SEARCH_ANSWER)})
        found = ArchiveCovers(gate=NoWait(), opener=opener, waiter=Pauses())
        offer = found.search("Turin Brakes", "Ether Song")
        assert offer.candidates == ()
        assert not offer.refused
