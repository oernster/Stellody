"""One scanned source, plus whatever a listener has stated about its album.

Split out of `grouping.py` when that file reached the length a module is
allowed here. The seam is a real one rather than an arbitrary slice: over there
is how folders and tags become albums, here is what a scan found and what
somebody has since said about it.

**An album edit is stated against a FOLDER, never against a handle.** A handle
is a digest of the album artist, the title and the year, so an edit to any of
those changes it: keyed by the handle, an edit would answer to the album it had
already stopped describing and would undo itself the moment it took effect. The
folder is where the music sits and says the same thing before and after.

That keying is also what makes two albums fold together. Give one the artist
and title another already carries and they resolve to a single handle, which is
how two disc folders of one release have always become one album. Nothing here
knows about folding; it simply hands assembly the values it should fold BY.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

from stellody.domain.ordering import TrackCandidate
from stellody.domain.overrides import AlbumEdit, AlbumField, album_index


@dataclass(frozen=True, slots=True)
class SourceEntry:
    """One scanned source, with the folder context needed to place it."""

    folder_name: str
    parent_path: str
    parent_name: str
    candidate: TrackCandidate
    album: str = ""
    album_artist: str = ""
    date: str = ""
    genre: str = ""


def folder_of(entry: SourceEntry) -> str:
    """Where an entry's music sits, which is what an album edit is stated against."""
    return f"{entry.parent_path}/{entry.folder_name}"


def stated_over(
    entries: tuple[SourceEntry, ...], edits: tuple[AlbumEdit, ...]
) -> tuple[SourceEntry, ...]:
    """The entries with every stated album value laid over them.

    Applied BEFORE anything is folded, so a stated artist or title is what the
    album is identified BY rather than a label hung on it afterwards.
    """
    if not edits:
        return entries
    # No second guard on the index being empty: an edit carries a value or it
    # cannot be built at all, so a non-empty set of them always indexes to
    # something. A branch nothing can reach is a branch nobody can check.
    stated = album_index(edits)
    laid: list[SourceEntry] = []
    for entry in entries:
        folder = folder_of(entry)
        artist = stated.get((folder, AlbumField.ALBUM_ARTIST))
        title = stated.get((folder, AlbumField.TITLE))
        date = stated.get((folder, AlbumField.DATE))
        genre = stated.get((folder, AlbumField.GENRE))
        if artist is None and title is None and date is None and genre is None:
            laid.append(entry)
            continue
        laid.append(
            replace(
                entry,
                album_artist=artist if artist is not None else entry.album_artist,
                album=title if title is not None else entry.album,
                date=date if date is not None else entry.date,
                genre=genre if genre is not None else entry.genre,
            )
        )
    return tuple(laid)
