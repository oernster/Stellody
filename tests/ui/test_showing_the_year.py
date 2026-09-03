"""A row shows the year, whatever shape the date tag was written in.

The tag is kept exactly as the file wrote it, which is right: the domain does
not get to decide that a date it did not understand was not worth keeping. What
follows from that is that the two places showing a date have to read a year out
of it rather than trust its shape.

Measured on a real iTunes rip: an M4A carries its date as a whole instant,
"2003-08-05T12:00:00Z". Taking the first four characters happened to work on
that one and does not work in general; printing the tag whole put the
instant in a row beside the genre. Both are pinned here.
"""

from __future__ import annotations

from stellody.domain.album import Album
from stellody.domain.identity import AlbumIdentity
from stellody.domain.track import CD_SAMPLE_RATE, Track, TrackSource
from stellody.ui.nodes import Node
from stellody.ui.row_text import Column, text_for

YEAR = "2003"
ISO_INSTANT = "2003-08-05T12:00:00Z"
PLAIN_DATE = "2003-05-12"
GENRE = "Electronic"


def _album(date: str) -> Album:
    return Album(
        identity=AlbumIdentity(
            album_artist="BT", title="Emotional Technology", date=date
        ),
        tracks=(
            Track(
                source=TrackSource(path="01 Paris.m4a"),
                disc_number=1,
                track_number=1,
                title="Paris",
                artists=("BT",),
                duration_ms=1000,
                sample_rate=CD_SAMPLE_RATE,
                bit_depth=0,
            ),
        ),
        genre=GENRE,
    )


def _detail(date: str) -> str:
    return text_for(Node(row=0, parent=None, album=_album(date)), Column.DETAIL)


def test_a_whole_instant_is_shown_as_its_year() -> None:
    """What an iTunes rip actually carries."""
    assert YEAR in _detail(ISO_INSTANT)
    assert "T12:00:00Z" not in _detail(ISO_INSTANT)


def test_a_dated_tag_is_shown_as_its_year() -> None:
    assert PLAIN_DATE not in _detail(PLAIN_DATE)
    assert YEAR in _detail(PLAIN_DATE)


def test_a_year_on_its_own_is_left_as_it_is() -> None:
    assert YEAR in _detail(YEAR)


def test_the_rest_of_the_row_is_unchanged() -> None:
    detail = _detail(ISO_INSTANT)
    assert GENRE in detail
    assert "1 track" in detail


def test_no_date_at_all_leaves_the_row_without_one() -> None:
    """An album with no date must not gain an empty gap where one would be."""
    assert _detail("").startswith(GENRE)
