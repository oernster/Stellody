"""Narrowing the library to the albums stated with what was asked for.

Any rather than all: each value asked for widens the set. A style asks for
that style alone, while the main it belongs to asks for every kind of itself,
which is what an album stating its main through its style gives for nothing.
"""

from __future__ import annotations

from factories import make_track

from stellody.domain.album import Album
from stellody.domain.identity import AlbumIdentity
from stellody.domain.narrowing import Narrowing, narrowed_to, stated_values
from stellody.domain.overrides import AlbumField


def _album(title: str, genre: str = "", artist: str = "Holst", date: str = "") -> Album:
    """One album stated with that genre, whatever it is called."""
    return Album(
        identity=AlbumIdentity(album_artist=artist, title=title, date=date),
        tracks=(make_track(title=f"{title} 1"),),
        genre=genre,
    )


ROCK = _album("Awesome", "Rock")
TRANCE = _album("Ambient", "Trance; Electronic")
HOUSE = _album("Deeper", "House; Electronic")
NOTHING = _album("Untagged")
UNREACHED = _album("Odd", "Progressive Rock")
LIBRARY = (ROCK, TRANCE, HOUSE, NOTHING, UNREACHED)


class TestWhatAnAlbumStates:
    def test_a_genre_is_read_as_the_catalogue_names_it_holds(self) -> None:
        assert stated_values(TRANCE, AlbumField.GENRE) == ("Electronic", "Trance")

    def test_a_tag_naming_nothing_in_the_catalogue_states_nothing(self) -> None:
        assert stated_values(UNREACHED, AlbumField.GENRE) == ()

    def test_an_untagged_album_states_nothing(self) -> None:
        assert stated_values(NOTHING, AlbumField.GENRE) == ()

    def test_the_other_fields_hold_one_value_each(self) -> None:
        album = _album("Planets", artist="Holst", date="1918")
        assert stated_values(album, AlbumField.ALBUM_ARTIST) == ("Holst",)
        assert stated_values(album, AlbumField.TITLE) == ("Planets",)
        assert stated_values(album, AlbumField.DATE) == ("1918",)

    def test_a_field_left_empty_states_nothing(self) -> None:
        """Which is what makes "not stated" reach it, whatever the field."""
        assert stated_values(_album("Planets"), AlbumField.DATE) == ()


class TestAskingForNothing:
    def test_everything_survives(self) -> None:
        assert narrowed_to(LIBRARY, Narrowing()) == LIBRARY

    def test_it_says_it_is_open(self) -> None:
        assert Narrowing().is_open
        assert not Narrowing(wanted=("Rock",)).is_open
        assert not Narrowing(unstated=True).is_open


class TestAskingForGenres:
    def test_one_genre_holds_the_albums_stated_with_it(self) -> None:
        assert narrowed_to(LIBRARY, Narrowing(wanted=("Rock",))) == (ROCK,)

    def test_two_genres_hold_the_union_of_both(self) -> None:
        """Ruled by Oliver: each tick widens the set rather than narrowing it."""
        asked = Narrowing(wanted=("Rock", "House"))
        assert narrowed_to(LIBRARY, asked) == (ROCK, HOUSE)

    def test_a_main_holds_every_kind_of_itself(self) -> None:
        asked = Narrowing(wanted=("Electronic",))
        assert narrowed_to(LIBRARY, asked) == (TRANCE, HOUSE)

    def test_a_style_holds_that_style_alone(self) -> None:
        asked = Narrowing(wanted=("Trance",))
        assert narrowed_to(LIBRARY, asked) == (TRANCE,)

    def test_a_genre_nothing_states_holds_nothing(self) -> None:
        assert narrowed_to(LIBRARY, Narrowing(wanted=("Reggae",))) == ()


class TestAskingForWhatIsNotStated:
    def test_it_holds_the_albums_with_no_genre_at_all(self) -> None:
        asked = Narrowing(unstated=True)
        assert narrowed_to(LIBRARY, asked) == (NOTHING, UNREACHED)

    def test_a_tag_naming_nothing_is_one_of_them(self) -> None:
        """No tick could ever reach it, so the box that reaches nothing must."""
        assert UNREACHED in narrowed_to(LIBRARY, Narrowing(unstated=True))

    def test_it_joins_the_genres_asked_for_rather_than_replacing_them(self) -> None:
        asked = Narrowing(wanted=("Rock",), unstated=True)
        assert narrowed_to(LIBRARY, asked) == (ROCK, NOTHING, UNREACHED)


class TestOtherFields:
    def test_an_artist_is_asked_the_same_way(self) -> None:
        """The dialog offers genre alone today; the shape takes the rest."""
        library = (_album("Planets", artist="Holst"), _album("Sea", artist="Bax"))
        asked = Narrowing(field=AlbumField.ALBUM_ARTIST, wanted=("Bax",))
        assert narrowed_to(library, asked) == (library[1],)
