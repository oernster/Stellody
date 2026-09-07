"""Asking two catalogues what a library is missing, without asking anything.

Every answer here is handed to the client rather than fetched, so what is
tested is the reading of an answer and the turning of a failure into something
the service above knows what to do with. The fetcher itself is tested against a
real service in `test_fetching.py`; neither client holds a socket, which is why
they can be asked everything here without one.
"""

from __future__ import annotations

import pytest

from stellody.application.choosing_covers import Wanted, always_wanted
from stellody.domain.matching import ReleaseKind
from stellody.infrastructure.catalogue import (
    ARTIST_URL,
    RELEASE_GROUP_URL,
    MusicBrainz,
)
from stellody.infrastructure.similarity import ALGORITHM, SIMILAR_URL, ListenBrainz

# How many similar artists the tests ask for. The figure a run uses is settled
# in the application layer; here it only has to be a number.
SOME = 10


class Answering:
    """A fetcher handing back one prepared answer and recording the ask.

    Address and parameters are kept apart rather than joined into a URL, so
    what is asserted is what the client asked for rather than how the fetcher
    happens to spell it.
    """

    def __init__(self, body: object) -> None:
        self._body = body
        self.addresses: list[str] = []
        self.parameters: list[dict[str, str]] = []
        self.wanted: list[Wanted] = []

    def json(
        self,
        address: str,
        parameters: dict[str, str],
        wanted: Wanted = always_wanted,
    ) -> object:
        """Record what was asked for, then answer with the prepared body."""
        self.addresses.append(address)
        self.parameters.append(dict(parameters))
        self.wanted.append(wanted)
        return self._body


def fetching(body: object) -> Answering:
    """A fetcher stand-in that answers with this and remembers the asking."""
    return Answering(body)


class TestHandingTheQuestionDown:
    """A client passes on whether anybody still wants the answer."""

    def test_every_question_carries_whether_it_is_still_wanted(self) -> None:
        """Otherwise a request in flight outlives the run that asked it."""
        given: Wanted = lambda: False
        fetch = fetching({"artists": []})
        MusicBrainz(fetch).identify("U2", given)
        MusicBrainz(fetch).albums_of("id", given)
        MusicBrainz(fetch).genres_of("id", given)
        ListenBrainz(fetch).similar_to("id", SOME, given)
        assert fetch.wanted == [given, given, given, given]

    def test_a_caller_with_nothing_to_stop_leaves_it_alone(self) -> None:
        """The default is a question nobody has to answer."""
        fetch = fetching({"artists": []})
        MusicBrainz(fetch).identify("U2")
        assert fetch.wanted == [always_wanted]


class TestIdentifyingAnArtist:
    """A name is only taken as identified where it matches exactly."""

    def test_one_exact_match_is_the_artist(self) -> None:
        """The ordinary case, being the only one that yields a lookup."""
        body = {"artists": [{"id": "u2-id", "name": "U2"}]}
        fetch = fetching(body)
        assert MusicBrainz(fetch).identify("U2") == ("u2-id",)
        assert fetch.addresses == [ARTIST_URL]

    def test_a_ranked_near_miss_is_not_the_artist(self) -> None:
        """Accepting the top hit files a discography under whoever ranked first."""
        body = {"artists": [{"id": "other", "name": "U2 Tribute Band"}]}
        assert MusicBrainz(fetching(body)).identify("U2") == ()

    def test_two_exact_matches_are_both_returned(self) -> None:
        """Ambiguity is an answer for somebody to be told about."""
        body = {
            "artists": [
                {"id": "us", "name": "Nirvana"},
                {"id": "uk", "name": "nirvana"},
            ]
        }
        assert MusicBrainz(fetching(body)).identify("Nirvana") == ("us", "uk")

    def test_an_entry_with_no_identifier_is_passed_over(self) -> None:
        """Nothing can be looked up by an artist with no identifier."""
        body = {"artists": [{"name": "U2"}]}
        assert MusicBrainz(fetching(body)).identify("U2") == ()

    def test_a_quote_in_a_name_cannot_break_the_search(self) -> None:
        """A term goes inside a quoted phrase, so it may not carry one."""
        fetch = fetching({"artists": []})
        MusicBrainz(fetch).identify('The "Band"')
        assert '"Band"' not in fetch.parameters[0]["query"]

    @pytest.mark.parametrize("body", [[], "not a dict", {"artists": "not a list"}])
    def test_an_answer_of_the_wrong_shape_names_nobody(self, body: object) -> None:
        """A service that changed shape answers nothing, rather than raising."""
        assert MusicBrainz(fetching(body)).identify("U2") == ()


class TestWhatAnArtistReleased:
    """Release groups, which is why the matching rule can be short."""

    def test_albums_arrive_with_their_kinds_and_genres(self) -> None:
        """Kinds as data rather than words in a title."""
        body = {
            "release-groups": [
                {
                    "title": "Secret World Live",
                    "primary-type": "Album",
                    "secondary-types": ["Live"],
                    "genres": [{"name": "Rock"}],
                }
            ]
        }
        fetch = fetching(body)
        found = MusicBrainz(fetch).albums_of("pg-id")
        assert fetch.addresses == [RELEASE_GROUP_URL]
        assert found[0].title == "Secret World Live"
        assert found[0].kinds == (ReleaseKind.LIVE,)
        assert found[0].genres == ("Rock",)

    def test_a_kind_nobody_anticipated_is_carried_as_other(self) -> None:
        """Excluded by the offering rule rather than passing as a plain album."""
        body = {
            "release-groups": [
                {
                    "title": "An Interview",
                    "primary-type": "Album",
                    "secondary-types": ["Interview"],
                }
            ]
        }
        found = MusicBrainz(fetching(body)).albums_of("id")
        assert found[0].kinds == (ReleaseKind.OTHER,)
        assert not found[0].is_offered

    def test_a_single_is_not_a_record_somebody_goes_looking_for(self) -> None:
        """Only albums and EPs are offered."""
        body = {
            "release-groups": [
                {"title": "A Single", "primary-type": "Single"},
                {"title": "An EP", "primary-type": "EP"},
                {"title": "", "primary-type": "Album"},
            ]
        }
        found = MusicBrainz(fetching(body)).albums_of("id")
        assert [group.title for group in found] == ["An EP"]

    def test_a_genre_list_of_the_wrong_shape_states_nothing(self) -> None:
        """An album described oddly is kept and marked as undescribed."""
        body = {
            "release-groups": [
                {"title": "A Record", "primary-type": "Album", "genres": "Rock"}
            ]
        }
        assert MusicBrainz(fetching(body)).albums_of("id")[0].genres == ()


class TestWhatAnArtistPlays:
    """The lookup that makes the result filter affordable."""

    def test_the_genres_are_read(self) -> None:
        """One ask per candidate per run, so it has to answer usefully."""
        body = {"genres": [{"name": "Rock"}, {"name": "Pop"}]}
        fetch = fetching(body)
        assert MusicBrainz(fetch).genres_of("pg-id") == ("Rock", "Pop")
        assert fetch.addresses == [f"{ARTIST_URL}/pg-id"]

    def test_an_answer_of_the_wrong_shape_says_nothing(self) -> None:
        """Which keeps the candidate rather than dropping it."""
        assert MusicBrainz(fetching([])).genres_of("id") == ()

    def test_a_nameless_genre_is_passed_over(self) -> None:
        """A genre with no name describes nothing."""
        body = {"genres": [{"name": ""}, {"count": 3}, "Rock"]}
        assert MusicBrainz(fetching(body)).genres_of("id") == ()


class TestWhoResemblesWhom:
    """The other half of a run, hence the reason there are two services."""

    def test_the_artists_arrive_ranked_as_the_service_ranked_them(self) -> None:
        """No opinion of ours is applied; it knows more about it than we do."""
        body = [
            {"artist_mbid": "a", "name": "Talk Talk"},
            {"artist_mbid": "b", "name": "The Blue Nile"},
        ]
        fetch = fetching(body)
        found = ListenBrainz(fetch).similar_to("pg-id", SOME)
        assert [artist.name for artist in found] == ["Talk Talk", "The Blue Nile"]
        assert fetch.addresses == [SIMILAR_URL]
        assert fetch.parameters[0]["algorithm"] == ALGORITHM

    def test_only_as_many_as_were_wanted(self) -> None:
        """Ten is the figure the plan settled on, applied here."""
        body = [{"artist_mbid": str(n), "name": f"Artist {n}"} for n in range(20)]
        assert len(ListenBrainz(fetching(body)).similar_to("id", SOME)) == SOME

    def test_an_entry_nobody_could_be_told_about_is_passed_over(self) -> None:
        """A candidate with no name is not a candidate."""
        body = [{"artist_mbid": "a", "name": ""}, "not a dict", {"name": "Real"}]
        found = ListenBrainz(fetching(body)).similar_to("id", SOME)
        assert [artist.name for artist in found] == ["Real"]

    def test_an_answer_of_the_wrong_shape_resembles_nobody(self) -> None:
        """A service that changed shape loses one artist, not a run."""
        assert ListenBrainz(fetching({"error": "no"})).similar_to("id", SOME) == ()
