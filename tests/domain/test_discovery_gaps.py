"""Working out what a library is missing, from what it holds.

No source, no network and no library on disk: everything here is values in and
values out, which is the diagnostic that says the foundation is sound.
"""

from __future__ import annotations

import pytest
from factories import make_track

from stellody.domain.album import Album
from stellody.domain.discovery import (
    Gaps,
    ReleaseGroup,
    SimilarArtist,
    albums_missing,
    artists_missing,
    catalogue_genres,
    held_matches,
    source_artists,
    wanted_by,
)
from stellody.domain.identity import AlbumIdentity
from stellody.domain.matching import ReleaseKind


def make_album(artist: str, title: str, genre: str = "Rock") -> Album:
    """A held album, described by the three things discovery reads."""
    return Album(
        identity=AlbumIdentity(album_artist=artist, title=title),
        tracks=(make_track(),),
        genre=genre,
    )


def test_an_offered_album_needs_a_title() -> None:
    """Nothing can be matched or shown without one."""
    with pytest.raises(ValueError, match="needs a title"):
        ReleaseGroup(title="   ")


def test_a_similar_artist_needs_a_name() -> None:
    """An identifier alone names nobody a listener could look for."""
    with pytest.raises(ValueError, match="needs a name"):
        SimilarArtist(name="")


def test_gaps_knows_when_it_found_nothing() -> None:
    """An artist yielding nothing is not written down as though it did."""
    assert Gaps(artist="Holst").is_empty
    assert not Gaps(
        artist="Holst", albums=(ReleaseGroup(title="The Planets"),)
    ).is_empty
    assert not Gaps(artist="Holst", artists=(SimilarArtist(name="Elgar"),)).is_empty


def test_a_catalogue_genre_is_read_the_way_the_library_reads_it() -> None:
    """Each stated name on its own, so no separator has to be invented."""
    assert catalogue_genres(()) == ()
    assert catalogue_genres(("Rock",)) == ("Rock",)
    assert catalogue_genres(("nothing the catalogue here knows",)) == ()


def test_a_style_reaches_its_main() -> None:
    """Trance is electronic, so a run ticking Electronic finds it."""
    assert "Electronic" in catalogue_genres(("Trance",))


def test_what_is_wanted_by_the_ticks() -> None:
    """A tick is an ask; anything the catalogue could not describe survives it."""
    assert wanted_by(("Rock",), ("Rock",))
    assert not wanted_by(("Rock",), ("Jazz",))
    assert wanted_by((), ("Jazz",))
    assert wanted_by(("nothing anybody knows",), ("Jazz",))


def test_nothing_ticked_asks_about_nobody() -> None:
    """Narrowing reads an empty ask as no narrowing, which is the whole library."""
    assert source_artists((make_album("AC/DC", "Back In Black"),), ()) == ()


def test_the_artists_inside_the_ticked_genres() -> None:
    """The scoping that keeps a run naming a subset somebody chose."""
    albums = (
        make_album("AC/DC", "Back In Black", "Rock"),
        make_album("Miles Davis", "Kind of Blue", "Jazz"),
    )
    assert source_artists(albums, ("Jazz",)) == ("Miles Davis",)


def test_an_artist_is_asked_about_once() -> None:
    """Three albums by one artist is one artist to look up, not three."""
    albums = (
        make_album("The Script", "The Script"),
        make_album("The Script", "Science & Faith"),
    )
    assert source_artists(albums, ("Rock",)) == ("The Script",)


def test_held_albums_are_dropped() -> None:
    """The rule the whole feature rests on: nothing owned is offered back."""
    held = held_matches((make_album("U2", "The Joshua Tree"),))
    offered = (
        ReleaseGroup(title="The Joshua Tree (Remastered)"),
        ReleaseGroup(title="Achtung Baby"),
    )
    missing = albums_missing(held, offered, ("Rock",))
    assert [group.title for group in missing] == ["Achtung Baby"]


def test_a_live_record_is_a_gap_even_where_the_studio_one_is_held() -> None:
    """Same key, different kind, so holding one says nothing about the other."""
    held = held_matches((make_album("Peter Gabriel", "Secret World"),))
    offered = (ReleaseGroup(title="Secret World Live", kinds=(ReleaseKind.LIVE,)),)
    assert len(albums_missing(held, offered, ("Rock",))) == 1


def test_a_live_record_already_held_is_not_a_gap() -> None:
    """The library states its kind in the title; the catalogue states it as data."""
    held = held_matches((make_album("Peter Gabriel", "Secret World (Live)"),))
    offered = (ReleaseGroup(title="Secret World Live", kinds=(ReleaseKind.LIVE,)),)
    assert albums_missing(held, offered, ("Rock",)) == ()


def test_a_hits_package_is_not_a_discovery() -> None:
    """A compilation of an artist already held is noise rather than a gap."""
    offered = (
        ReleaseGroup(title="Greatest Hits", kinds=(ReleaseKind.COMPILATION,)),
        ReleaseGroup(title="Sessions", kinds=(ReleaseKind.OTHER,)),
        ReleaseGroup(title="Rarities", kinds=(ReleaseKind.DEMO,)),
    )
    missing = albums_missing(frozenset(), offered, ("Rock",))
    assert [group.title for group in missing] == ["Rarities"]


def test_candidate_albums_respect_the_ticks() -> None:
    """Ticking Folk and receiving a comedy record is the filter failing."""
    offered = (
        ReleaseGroup(title="A Folk Record", genres=("Folk",)),
        ReleaseGroup(title="A Comedy Record", genres=("Comedy",)),
    )
    missing = albums_missing(frozenset(), offered, ("Folk",))
    assert [group.title for group in missing] == ["A Folk Record"]


def test_unstated_genre_is_kept_and_marked() -> None:
    """Dropping what a catalogue failed to describe narrows discovery."""
    undescribed = ReleaseGroup(title="Something Obscure")
    assert undescribed.states_no_genre
    assert albums_missing(frozenset(), (undescribed,), ("Folk",)) == (undescribed,)


def test_a_described_album_is_not_marked_unstated() -> None:
    """The marking has to mean something, so it cannot be true of everything."""
    assert not ReleaseGroup(title="A Folk Record", genres=("Folk",)).states_no_genre


def test_held_artists_are_dropped() -> None:
    """An artist on the shelf is not somebody to go and find."""
    offered = (SimilarArtist(name="The Police"), SimilarArtist(name="Talk Talk"))
    missing = artists_missing(("the police",), offered)
    assert [artist.name for artist in missing] == ["Talk Talk"]


def test_an_artist_offered_twice_is_offered_once() -> None:
    """A catalogue naming somebody twice is still one artist to look for."""
    offered = (SimilarArtist(name="Talk Talk"), SimilarArtist(name="talk  talk"))
    assert len(artists_missing((), offered)) == 1
