"""FR-D99: both genre choosers narrow by year as well, with nothing installed.

The library's filter reads an album's date tag; the answer's filter reads the
year the catalogue gave each album offered. Either way an album stating no
year is left out while years are set. A similar artist has no year, so it is
left alone.
"""

from __future__ import annotations

from factories import make_track

from stellody.domain.album import Album
from stellody.domain.discovery import Gaps, ReleaseGroup, SimilarArtist
from stellody.domain.discovery_filter import released_within
from stellody.domain.identity import AlbumIdentity
from stellody.domain.narrowing import Narrowing, narrowed_to
from stellody.domain.release_years import ANY_YEAR, ReleaseYears

EIGHTIES = ReleaseYears(1980, 1989)


def held(title: str, date: str, genre: str = "Rock") -> Album:
    """An album in the library carrying this date tag."""
    return Album(
        identity=AlbumIdentity(album_artist="AC/DC", title=title, date=date),
        tracks=(make_track(),),
        genre=genre,
    )


BACK_IN_BLACK = held("Back in Black", "1980-07-25")
POWER_UP = held("Power Up", "2020")
UNDATED = held("Bootleg", "")


class TestTheLibrary:
    def test_years_alone_are_a_filter(self) -> None:
        assert not Narrowing(years=EIGHTIES).is_open
        assert Narrowing(years=ANY_YEAR).is_open

    def test_only_albums_dated_inside_the_years_are_kept(self) -> None:
        """A full date counts by its year; an undated album cannot fit."""
        kept = narrowed_to(
            (BACK_IN_BLACK, POWER_UP, UNDATED), Narrowing(years=EIGHTIES)
        )
        assert kept == (BACK_IN_BLACK,)

    def test_genres_and_years_must_both_hold(self) -> None:
        jazz = held("Kind of Blue", "1985", genre="Jazz")
        asked = Narrowing(wanted=("Rock",), years=EIGHTIES)
        assert narrowed_to((BACK_IN_BLACK, POWER_UP, jazz), asked) == (BACK_IN_BLACK,)

    def test_the_no_genre_box_answers_to_the_years_too(self) -> None:
        none_stated = held("Demo", "1984", genre="")
        later = held("Demo II", "1999", genre="")
        asked = Narrowing(unstated=True, years=EIGHTIES)
        assert narrowed_to((none_stated, later), asked) == (none_stated,)


EIGHTIES_ALBUM = ReleaseGroup(title="For Those About to Rock", released="1981")
LATER_ALBUM = ReleaseGroup(title="Rock or Bust", released="2014")
NO_DATE = ReleaseGroup(title="Live Somewhere")
AIRBOURNE = SimilarArtist(name="Airbourne", identifier="airbourne")


class TestTheAnswer:
    def test_every_year_leaves_the_answer_alone(self) -> None:
        answer = (Gaps("AC/DC", albums=(LATER_ALBUM,)),)
        assert released_within(answer, ANY_YEAR) == answer

    def test_only_albums_released_inside_the_years_are_shown(self) -> None:
        answer = (Gaps("AC/DC", albums=(EIGHTIES_ALBUM, LATER_ALBUM, NO_DATE)),)
        shown = released_within(answer, EIGHTIES)
        assert shown == (Gaps("AC/DC", albums=(EIGHTIES_ALBUM,)),)

    def test_similar_artists_have_no_year_and_stay(self) -> None:
        """The answer holds no year for a similar artist, so the years judge
        albums alone."""
        answer = (Gaps("AC/DC", albums=(LATER_ALBUM,), artists=(AIRBOURNE,)),)
        shown = released_within(answer, EIGHTIES)
        assert shown == (Gaps("AC/DC", artists=(AIRBOURNE,)),)

    def test_a_heading_left_with_nothing_is_not_shown(self) -> None:
        """FR-D75, series headings included."""
        answer = (
            Gaps("Global Underground", albums=(LATER_ALBUM,), series=True),
            Gaps("AC/DC", albums=(EIGHTIES_ALBUM,)),
        )
        assert released_within(answer, EIGHTIES) == (answer[1],)
