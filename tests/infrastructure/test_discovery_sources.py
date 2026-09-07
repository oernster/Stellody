"""Asking two catalogues what a library is missing, without asking anything.

Every answer here is handed to the client rather than fetched, so what is
tested is the reading of an answer and the turning of a failure into something
the service above knows what to do with.
"""

from __future__ import annotations

import io
import json
import urllib.error

import pytest

from stellody.application.discovery_ports import (
    RateRefused,
    SourceFailed,
    SourceUnavailable,
)
from stellody.domain.matching import ReleaseKind
from stellody.infrastructure.catalogue import (
    ARTIST_URL,
    RELEASE_GROUP_URL,
    MusicBrainz,
)
from stellody.infrastructure.courtesy import USER_AGENT
from stellody.infrastructure.fetching import Fetcher
from stellody.infrastructure.similarity import ALGORITHM, SIMILAR_URL, ListenBrainz


class Answering:
    """An opener handing back one prepared answer and recording the ask."""

    def __init__(self, body: object) -> None:
        self._body = body
        self.asked: list[str] = []
        self.agents: list[str] = []

    def __call__(self, request, timeout=None):
        """Record what was asked for, then answer with the prepared body."""
        self.asked.append(request.full_url)
        self.agents.append(request.get_header("User-agent"))
        return io.BytesIO(json.dumps(self._body).encode("utf-8"))


class Refusing:
    """An opener that always raises whatever it was given."""

    def __init__(self, trouble: Exception) -> None:
        self._trouble = trouble

    def __call__(self, request, timeout=None):
        """Fail the way this stand-in was told to."""
        raise self._trouble


class OpenGate:
    """A gate that lets everything through at once and counts the asks."""

    def __init__(self) -> None:
        self.waits = 0

    def wait(self, wanted=None) -> bool:
        """Let it through, having noted that permission was sought."""
        self.waits += 1
        return True


def fetching(body: object) -> tuple[Fetcher, Answering, OpenGate]:
    """A fetcher wired to an opener that answers with this."""
    opener = Answering(body)
    gate = OpenGate()
    return Fetcher(gate=gate, opener=opener), opener, gate


def failing(trouble: Exception) -> Fetcher:
    """A fetcher whose opener always fails this way."""
    return Fetcher(gate=OpenGate(), opener=Refusing(trouble))


def http_error(code: int) -> urllib.error.HTTPError:
    """An answer from a service that declined to give one."""
    return urllib.error.HTTPError(
        url="https://example.invalid", code=code, msg="no", hdrs=None, fp=None
    )


class TestTheFetcher:
    """The one module that opens a connection, asked without one."""

    def test_it_waits_its_turn_and_names_the_application(self) -> None:
        """The courtesies are applied here so no client can forget them."""
        fetcher, opener, gate = fetching({"ok": True})
        assert fetcher.json("https://example.invalid/a", {"q": "x"}) == {"ok": True}
        assert gate.waits == 1
        assert opener.agents == [USER_AGENT]

    def test_it_builds_the_query_so_a_client_needs_no_networking(self) -> None:
        """The reason the permitted-module list gained one name rather than two."""
        fetcher, opener, _ = fetching({})
        fetcher.json("https://example.invalid/a", {"q": "a b", "fmt": "json"})
        assert opener.asked == ["https://example.invalid/a?q=a+b&fmt=json"]

    @pytest.mark.parametrize("code", [429, 503])
    def test_a_refusal_is_asked_again_rather_than_reported(self, code: int) -> None:
        """The service asking for patience is not the service saying no."""
        with pytest.raises(RateRefused):
            failing(http_error(code)).json("https://example.invalid", {})

    def test_another_answer_is_that_artist_failing(self) -> None:
        """One artist nobody could answer about, rather than the run ending."""
        with pytest.raises(SourceFailed, match="500"):
            failing(http_error(500)).json("https://example.invalid", {})

    def test_nothing_answering_at_all_is_a_different_thing(self) -> None:
        """No connection means every later question fares the same way."""
        with pytest.raises(SourceUnavailable):
            failing(urllib.error.URLError("no route")).json("https://a.invalid", {})

    def test_an_answer_that_is_not_json_is_that_artist_failing(self) -> None:
        """A service changing shape is one artist lost, not a run."""
        fetcher = Fetcher(
            gate=OpenGate(), opener=lambda r, timeout=None: io.BytesIO(b"{")
        )
        with pytest.raises(SourceFailed, match="could not be read"):
            fetcher.json("https://example.invalid", {})


class TestIdentifyingAnArtist:
    """A name is only taken as identified where it matches exactly."""

    def test_one_exact_match_is_the_artist(self) -> None:
        """The ordinary case, being the only one that yields a lookup."""
        body = {"artists": [{"id": "u2-id", "name": "U2"}]}
        fetcher, opener, _ = fetching(body)
        assert MusicBrainz(fetcher).identify("U2") == ("u2-id",)
        assert opener.asked[0].startswith(ARTIST_URL)

    def test_a_ranked_near_miss_is_not_the_artist(self) -> None:
        """Accepting the top hit files a discography under whoever ranked first."""
        body = {"artists": [{"id": "other", "name": "U2 Tribute Band"}]}
        assert MusicBrainz(fetching(body)[0]).identify("U2") == ()

    def test_two_exact_matches_are_both_returned(self) -> None:
        """Ambiguity is an answer for somebody to be told about."""
        body = {
            "artists": [
                {"id": "us", "name": "Nirvana"},
                {"id": "uk", "name": "nirvana"},
            ]
        }
        assert MusicBrainz(fetching(body)[0]).identify("Nirvana") == ("us", "uk")

    def test_an_entry_with_no_identifier_is_passed_over(self) -> None:
        """Nothing can be looked up by an artist with no identifier."""
        body = {"artists": [{"name": "U2"}]}
        assert MusicBrainz(fetching(body)[0]).identify("U2") == ()

    def test_a_quote_in_a_name_cannot_break_the_search(self) -> None:
        """A term goes inside a quoted phrase, so it may not carry one."""
        fetcher, opener, _ = fetching({"artists": []})
        MusicBrainz(fetcher).identify('The "Band"')
        assert "%22Band%22" not in opener.asked[0]

    @pytest.mark.parametrize("body", [[], "not a dict", {"artists": "not a list"}])
    def test_an_answer_of_the_wrong_shape_names_nobody(self, body: object) -> None:
        """A service that changed shape answers nothing, rather than raising."""
        assert MusicBrainz(fetching(body)[0]).identify("U2") == ()


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
        fetcher, opener, _ = fetching(body)
        found = MusicBrainz(fetcher).albums_of("pg-id")
        assert opener.asked[0].startswith(RELEASE_GROUP_URL)
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
        found = MusicBrainz(fetching(body)[0]).albums_of("id")
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
        found = MusicBrainz(fetching(body)[0]).albums_of("id")
        assert [group.title for group in found] == ["An EP"]

    def test_a_genre_list_of_the_wrong_shape_states_nothing(self) -> None:
        """An album described oddly is kept and marked as undescribed."""
        body = {
            "release-groups": [
                {"title": "A Record", "primary-type": "Album", "genres": "Rock"}
            ]
        }
        assert MusicBrainz(fetching(body)[0]).albums_of("id")[0].genres == ()


class TestWhatAnArtistPlays:
    """The lookup that makes the result filter affordable."""

    def test_the_genres_are_read(self) -> None:
        """One ask per candidate per run, so it has to answer usefully."""
        body = {"genres": [{"name": "Rock"}, {"name": "Pop"}]}
        assert MusicBrainz(fetching(body)[0]).genres_of("id") == ("Rock", "Pop")

    def test_an_answer_of_the_wrong_shape_says_nothing(self) -> None:
        """Which keeps the candidate rather than dropping it."""
        assert MusicBrainz(fetching([])[0]).genres_of("id") == ()

    def test_a_nameless_genre_is_passed_over(self) -> None:
        """A genre with no name describes nothing."""
        body = {"genres": [{"name": ""}, {"count": 3}, "Rock"]}
        assert MusicBrainz(fetching(body)[0]).genres_of("id") == ()


class TestWhoResemblesWhom:
    """The other half of a run, hence the reason there are two services."""

    def test_the_artists_arrive_ranked_as_the_service_ranked_them(self) -> None:
        """No opinion of ours is applied; it knows more about it than we do."""
        body = [
            {"artist_mbid": "a", "name": "Talk Talk"},
            {"artist_mbid": "b", "name": "The Blue Nile"},
        ]
        fetcher, opener, _ = fetching(body)
        found = ListenBrainz(fetcher).similar_to("pg-id", 10)
        assert [artist.name for artist in found] == ["Talk Talk", "The Blue Nile"]
        assert opener.asked[0].startswith(SIMILAR_URL)
        assert ALGORITHM in opener.asked[0]

    def test_only_as_many_as_were_wanted(self) -> None:
        """Ten is the figure the plan settled on, applied here."""
        body = [{"artist_mbid": str(n), "name": f"Artist {n}"} for n in range(20)]
        assert len(ListenBrainz(fetching(body)[0]).similar_to("id", 10)) == 10

    def test_an_entry_nobody_could_be_told_about_is_passed_over(self) -> None:
        """A candidate with no name is not a candidate."""
        body = [{"artist_mbid": "a", "name": ""}, "not a dict", {"name": "Real"}]
        found = ListenBrainz(fetching(body)[0]).similar_to("id", 10)
        assert [artist.name for artist in found] == ["Real"]

    def test_an_answer_of_the_wrong_shape_resembles_nobody(self) -> None:
        """A service that changed shape loses one artist, not a run."""
        assert ListenBrainz(fetching({"error": "no"})[0]).similar_to("id", 10) == ()
