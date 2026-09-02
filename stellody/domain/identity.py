"""Album identity: what makes two files part of the same album."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

from stellody.domain.text import (
    comparison_key,
    is_various_artists,
    normalise,
    sort_key,
    year_of,
)

HANDLE_LENGTH = 16
# The name this length went by while artwork was the only thing keyed on it.
ART_KEY_LENGTH = HANDLE_LENGTH


@dataclass(frozen=True, slots=True)
class AlbumIdentity:
    """The tuple that decides which album a track belongs to.

    Deliberately built from tags rather than from folder paths, so an album
    survives being moved or renamed on disk.
    """

    album_artist: str
    title: str
    date: str = ""

    def __post_init__(self) -> None:
        if not self.album_artist:
            raise ValueError("an album needs an album artist")
        if not self.title:
            raise ValueError("an album needs a title")

    @property
    def key(self) -> tuple[str, str, str]:
        """The value two albums are compared on."""
        return (
            comparison_key(self.album_artist),
            comparison_key(self.title),
            str(year_of(self.date) or ""),
        )

    @property
    def sort_key(self) -> tuple[str, int, str]:
        """Ordering: by artist, then chronologically, then by title."""
        return (
            sort_key(self.album_artist),
            year_of(self.date) or 0,
            sort_key(self.title),
        )

    @property
    def handle(self) -> str:
        """A stable short name for this album, for anything keyed on it.

        Derived from identity rather than from a path, so a rescan after a
        folder rename or a re-rip finds the same album again. Three things are
        keyed on it: cached artwork, the album's own rating and the corrections
        a listener has accepted. It is stated ONCE here rather than digested
        again wherever it is wanted, since three spellings of one value is three
        chances for two of them to drift apart.
        """
        material = " ".join(self.key).encode("utf-8")
        return hashlib.sha256(material).hexdigest()[:HANDLE_LENGTH]

    @property
    def art_key(self) -> str:
        """The handle, under the name the artwork cache reaches it by."""
        return self.handle

    @property
    def is_compilation(self) -> bool:
        """True when this album is credited to various artists."""
        return is_various_artists(self.album_artist)

    @property
    def display_title(self) -> str:
        """The album title as it should be shown."""
        return normalise(self.title)

    @property
    def display_artist(self) -> str:
        """The album artist as it should be shown."""
        return normalise(self.album_artist)
