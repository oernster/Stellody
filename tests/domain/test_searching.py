"""Narrowing the library, then naming what a phrase actually hit.

An album is kept whole: a phrase that hits one track leaves the album reading
the way it always does. What the hit gives is somewhere to put the highlight.
"""

from __future__ import annotations

import pytest
from factories import make_track

from stellody.domain.album import Album
from stellody.domain.identity import AlbumIdentity
from stellody.domain.searching import (
    AlbumText,
    Found,
    Search,
    hits,
    narrowed,
    prepared,
)
from stellody.domain.track import Track, TrackSource


def _track(title: str, number: int = 1, *artists: str) -> Track:
    """One track with a title, plus its own artists where it matters."""
    return make_track(
        source=TrackSource(path=f"{number:02d} {title}.flac"),
        track_number=number,
        title=title,
        artists=artists or ("Holst",),
    )


def _album(*tracks: Track, title: str = "The Planets", artist: str = "Holst") -> Album:
    """An album holding these tracks."""
    return Album(
        identity=AlbumIdentity(album_artist=artist, title=title), tracks=tracks
    )


PLANETS = _album(_track("Venus", 1), _track("Mars", 2))
SIMPLE = _album(_track("Destiny", 1), title="Simple Things", artist="Zero 7")


class TestSearch:
    def test_an_empty_phrase_asks_for_nothing(self) -> None:
        assert Search().is_open
        assert Search(phrase="   ").is_open

    def test_a_phrase_is_compared_folded(self) -> None:
        assert Search(phrase="  VeNuS  ").key == "venus"
        assert not Search(phrase="Venus").is_open


class TestAlbumText:
    def test_every_track_needs_its_own_key(self) -> None:
        with pytest.raises(ValueError):
            AlbumText(album=PLANETS, key="the planets", track_keys=("venus",))

    def test_preparing_folds_the_album_and_its_tracks(self) -> None:
        (entry,) = prepared((PLANETS,))
        assert entry.album is PLANETS
        assert entry.key == "the planets holst"
        assert entry.track_keys == ("venus holst", "mars holst")


class TestHits:
    def test_asking_for_nothing_points_at_nothing(self) -> None:
        (entry,) = prepared((PLANETS,))
        assert hits(entry, Search()) == ()

    def test_a_track_title_is_hit(self) -> None:
        (entry,) = prepared((PLANETS,))
        (hit,) = hits(entry, Search(phrase="venus"))
        assert hit.title == "Venus"

    def test_a_track_artist_is_hit(self) -> None:
        (entry,) = prepared((_album(_track("Aria", 1, "Emiliana Torrini")),))
        (hit,) = hits(entry, Search(phrase="torrini"))
        assert hit.title == "Aria"

    def test_a_phrase_inside_no_track_hits_nothing(self) -> None:
        (entry,) = prepared((PLANETS,))
        assert hits(entry, Search(phrase="saturn")) == ()


class TestNarrowing:
    def test_asking_for_nothing_keeps_everything(self) -> None:
        found = narrowed(prepared((PLANETS, SIMPLE)), Search())
        assert [one.album for one in found] == [PLANETS, SIMPLE]
        assert all(one.tracks == () for one in found)

    def test_an_album_title_keeps_the_album_and_points_nowhere(self) -> None:
        (one,) = narrowed(prepared((PLANETS, SIMPLE)), Search(phrase="simple"))
        assert one.album is SIMPLE
        assert one.tracks == ()

    def test_an_album_artist_keeps_the_album(self) -> None:
        (one,) = narrowed(prepared((PLANETS, SIMPLE)), Search(phrase="zero 7"))
        assert one.album is SIMPLE

    def test_a_track_keeps_the_whole_album_and_names_the_track(self) -> None:
        """B: every track stays, so the album reads as it always does."""
        (one,) = narrowed(prepared((PLANETS, SIMPLE)), Search(phrase="venus"))
        assert one.album is PLANETS
        assert one.album.track_count == 2
        assert [track.title for track in one.tracks] == ["Venus"]

    def test_an_album_matching_nowhere_is_dropped(self) -> None:
        assert narrowed(prepared((PLANETS, SIMPLE)), Search(phrase="saturn")) == ()


class TestFound:
    def test_an_album_matched_by_its_own_name_points_at_no_track(self) -> None:
        assert Found(album=PLANETS).tracks == ()
