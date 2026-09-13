"""FR-D54 and FR-D55: narrowing an answer to some of the genres it looked in.

Values in and values out: an answer, the library as it stands and what the
catalogue memory records, with no dialog and no file.
"""

from __future__ import annotations

from factories import make_track

from stellody.domain.album import Album
from stellody.domain.discovery import (
    Gaps,
    ReleaseGroup,
    SimilarArtist,
    filtered_answer,
)
from stellody.domain.identity import AlbumIdentity

HOUSE = ("House",)
# What the catalogue memory holds for a candidate: the catalogue's own words.
REMEMBERED = {"a-house-act": ("house",), "a-rock-act": ("rock",)}


def held(artist: str, genre: str) -> Album:
    """An album in the library, filed under this artist in this genre."""
    return Album(
        identity=AlbumIdentity(album_artist=artist, title=f"{artist} Album"),
        tracks=(make_track(),),
        genre=genre,
    )


LIBRARY = (held("Tinlicker", "House"), held("AC/DC", "Rock"))
TINLICKER = Gaps(artist="Tinlicker", albums=(ReleaseGroup(title="Remote Places"),))
ACDC = Gaps(artist="AC/DC", albums=(ReleaseGroup(title="Power Up"),))


def test_nothing_picked_shows_everything() -> None:
    """No filter is the whole answer, with nothing said to be withheld."""
    shown = filtered_answer((TINLICKER, ACDC), LIBRARY, REMEMBERED, ())
    assert shown.gaps == (TINLICKER, ACDC)
    assert shown.unjudged == 0


def test_a_source_artist_shows_by_the_genres_held() -> None:
    """Judged by the genre on the listener's own album, never the catalogue's."""
    shown = filtered_answer((TINLICKER, ACDC), LIBRARY, REMEMBERED, HOUSE)
    assert shown.gaps == (TINLICKER,)


def test_a_candidate_shows_by_its_remembered_genres() -> None:
    """A candidate is not in the library, so the memory is what judges them."""
    house = SimilarArtist(name="Lane 8", identifier="a-house-act")
    rock = SimilarArtist(name="Airbourne", identifier="a-rock-act")
    answer = (Gaps(artist="AC/DC", artists=(house, rock)),)
    shown = filtered_answer(answer, LIBRARY, REMEMBERED, HOUSE)
    assert shown.gaps == (Gaps(artist="AC/DC", artists=(house,)),)


def test_an_artist_with_nothing_left_is_not_shown() -> None:
    """A heading over nothing is a row that says nothing."""
    rock = SimilarArtist(name="Airbourne", identifier="a-rock-act")
    answer = (Gaps(artist="AC/DC", albums=ACDC.albums, artists=(rock,)),)
    assert filtered_answer(answer, LIBRARY, REMEMBERED, HOUSE).gaps == ()


def test_candidates_with_no_genre_are_counted_as_withheld() -> None:
    """Counted once each, however many source artists they were offered under."""
    quiet = SimilarArtist(name="Nobody Knows", identifier="unremembered")
    silent = SimilarArtist(name="Nor Them", identifier="also-unremembered")
    answer = (
        Gaps(artist="Tinlicker", artists=(quiet, silent)),
        Gaps(artist="AC/DC", artists=(quiet,)),
    )
    assert filtered_answer(answer, LIBRARY, REMEMBERED, HOUSE).unjudged == 2
