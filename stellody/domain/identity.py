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

ART_KEY_LENGTH = 16


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
    def art_key(self) -> str:
        """A stable handle for cached artwork.

        Derived from identity rather than from a path, so a rescan after a
        folder rename reuses the cached image instead of refetching it.
        """
        material = " ".join(self.key).encode("utf-8")
        return hashlib.sha256(material).hexdigest()[:ART_KEY_LENGTH]

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
