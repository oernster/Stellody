"""What each cell of the album tree says.

Kept apart from the model because the two answer different questions: this is
what a row reads as, while the model is Qt's questions about rows. A column
added here is a change to what the library says about itself; a change there
is a change to how Qt is answered.
"""

from __future__ import annotations

from enum import IntEnum

from stellody.domain.album import Album, Disc
from stellody.domain.track import Track
from stellody.ui.nodes import Node

MILLISECONDS_PER_SECOND = 1000
SECONDS_PER_MINUTE = 60
MINUTES_PER_HOUR = 60

HEADINGS = ("Title", "Artist", "Detail", "Length")


class Column(IntEnum):
    """The columns the tree shows."""

    TITLE = 0
    ARTIST = 1
    DETAIL = 2
    LENGTH = 3


def format_duration(milliseconds: int) -> str:
    """A duration as h:mm:ss; m:ss when it is under an hour."""
    seconds = milliseconds // MILLISECONDS_PER_SECOND
    minutes, seconds = divmod(seconds, SECONDS_PER_MINUTE)
    hours, minutes = divmod(minutes, MINUTES_PER_HOUR)
    if hours:
        return f"{hours}:{minutes:02d}:{seconds:02d}"
    return f"{minutes}:{seconds:02d}"


def _album_text(album: Album, column: Column) -> str:
    """One cell of an album row."""
    if column is Column.TITLE:
        return album.identity.display_title
    if column is Column.ARTIST:
        return album.identity.display_artist
    if column is Column.LENGTH:
        return format_duration(album.duration_ms)
    parts = [part for part in (album.identity.date, album.genre) if part]
    parts.append(f"{album.track_count} tracks")
    if album.disc_count > 1:
        parts.append(f"{album.disc_count} discs")
    return "  ".join(parts)


def _disc_text(disc: Disc, column: Column) -> str:
    """One cell of a disc row."""
    if column is Column.TITLE:
        return f"Disc {disc.number}"
    if column is Column.DETAIL:
        return f"{len(disc.tracks)} tracks"
    if column is Column.LENGTH:
        return format_duration(disc.duration_ms)
    return ""


def _track_text(track: Track, column: Column) -> str:
    """One cell of a track row."""
    if column is Column.TITLE:
        return f"{track.track_number:>2}.  {track.title}"
    if column is Column.ARTIST:
        return track.artist_text
    if column is Column.LENGTH:
        return format_duration(track.duration_ms)
    if track.is_high_resolution:
        return f"{track.sample_rate // MILLISECONDS_PER_SECOND} kHz / {track.bit_depth}"
    return ""


def detail_text(known: str, plays: int) -> str:
    """A track's detail cell: what it already said, plus what it has been played.

    Nothing at all until it has played once. A column of noughts says only
    that the library is new, while a column with a few numbers in it says
    which records somebody keeps coming back to, which is the whole point.
    """
    if plays == 0:
        return known
    counted = f"{plays} play" + ("" if plays == 1 else "s")
    return f"{known}  {counted}" if known else counted


def text_for(node: Node, column: Column) -> str:
    """The display text for any node."""
    if node.album is not None:
        return _album_text(node.album, column)
    if node.disc is not None:
        return _disc_text(node.disc, column)
    return _track_text(node.track, column)  # type: ignore[arg-type]
