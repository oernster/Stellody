"""Narrowing the library to what somebody is looking for.

Pure, deliberately without an index of its own. Measured at the reference
library's size, a pass over text already normalised costs a small fraction of
the time a typed character allows, so a keystroke can afford a whole one.
A stored index would also hold the wrong text: the store keeps raw tags
while the library shows resolved ones, so a title the resolver corrected would
be unfindable and a damaged one would match a row nobody can see.

**Normalising is done once, not once a keystroke.** Measured, `comparison_key`
over every title in the library costs tens of times what a plain fold does;
the answer never changes between keystrokes. So an album's text is prepared
when the library is assembled and a keystroke does substring tests alone.

**An album is kept whole.** A phrase that hits one track keeps every track, so
an album reads the way it always does. What the hit gives is somewhere to put
the highlight, which `Found.tracks` names.
"""

from __future__ import annotations

from dataclasses import dataclass

from stellody.domain.album import Album
from stellody.domain.text import comparison_key
from stellody.domain.track import Track


@dataclass(frozen=True, slots=True)
class Search:
    """What the library is being narrowed to.

    A condition rather than a phrase alone, so that a rating or a play count
    can join it without every caller changing. Neither column exists yet; this
    is the shape that lets one arrive without a rewrite.
    """

    phrase: str = ""

    @property
    def key(self) -> str:
        """The phrase as it is compared."""
        return comparison_key(self.phrase)

    @property
    def is_open(self) -> bool:
        """True while nothing is being asked for, so everything survives."""
        return not self.key


@dataclass(frozen=True, slots=True)
class AlbumText:
    """One album's searchable text, normalised once.

    The album's own key covers its title and artist together; a track carries
    its own so a hit can name the track rather than only the album.
    """

    album: Album
    key: str
    track_keys: tuple[str, ...]

    def __post_init__(self) -> None:
        if len(self.track_keys) != len(self.album.tracks):
            raise ValueError("every track needs its own key")


@dataclass(frozen=True, slots=True)
class Found:
    """An album that survived, with the tracks the phrase actually hit.

    An empty tuple of tracks is not an error: the album's own title or artist
    matched, so there is nothing inside it to point at.
    """

    album: Album
    tracks: tuple[Track, ...] = ()


def _track_text(track: Track) -> str:
    """Everything about one track that is worth searching."""
    return comparison_key(" ".join((track.title,) + track.artists))


def prepared(albums: tuple[Album, ...]) -> tuple[AlbumText, ...]:
    """Each album with its text normalised, ready to be searched cheaply."""
    return tuple(
        AlbumText(
            album=album,
            key=comparison_key(f"{album.identity.title} {album.identity.album_artist}"),
            track_keys=tuple(_track_text(track) for track in album.tracks),
        )
        for album in albums
    )


def hits(entry: AlbumText, search: Search) -> tuple[Track, ...]:
    """The tracks this phrase points at inside one album."""
    if search.is_open:
        return ()
    key = search.key
    return tuple(
        track
        for track, text in zip(entry.album.tracks, entry.track_keys)
        if key in text
    )


def narrowed(entries: tuple[AlbumText, ...], search: Search) -> tuple[Found, ...]:
    """The albums that survive, each kept whole, hit tracks named.

    An album survives on its own title or artist, else on any track inside it.
    Asking for nothing keeps everything and points at nothing, which is what
    clearing the box has to do.
    """
    if search.is_open:
        return tuple(Found(album=entry.album) for entry in entries)
    key = search.key
    found = []
    for entry in entries:
        tracks = hits(entry, search)
        if key in entry.key or tracks:
            found.append(Found(album=entry.album, tracks=tracks))
    return tuple(found)
