"""Album identity: what makes two files part of the same album."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, replace

from stellody.domain.text import (
    comparison_key,
    is_various_artists,
    normalise,
    sort_key,
    year_of,
)

HANDLE_LENGTH = 16


def _digest(material: str) -> str:
    """One short handle for a run of text."""
    return hashlib.sha256(material.encode("utf-8")).hexdigest()[:HANDLE_LENGTH]


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
    # Empty for almost every album, deliberately so. Tags alone cannot tell
    # two recordings of one work apart: a symphony under two conductors carries
    # one composer, one title and often one year, so both would answer to the
    # same handle and would then share a cached cover, an album rating and every
    # track rating under it. Where assembly finds two albums resolving alike it
    # gives each the place it was found, which is the only thing that separates
    # them. An album nothing collides with keeps an empty one, so its handle is
    # exactly what it always was and nothing it has been told is orphaned.
    discriminator: str = ""

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
    def handle_parts(self) -> tuple[str, ...]:
        """What everything keyed on this album is digested from.

        The discriminator is APPENDED where there is one and left out entirely
        where there is not, rather than joined in as an empty string. An album
        nothing collides with therefore digests exactly the run of text it
        always did, so its cover, its rating and every rating under it are
        found again rather than orphaned by this rule arriving.
        """
        if not self.discriminator:
            return self.key
        return self.key + (self.discriminator,)

    def told_apart_by(self, place: str) -> AlbumIdentity:
        """The same album, separated from another that resolves exactly alike.

        Digested rather than carried whole, so one long path cannot make a key
        that is mostly one album's folder name.
        """
        return replace(self, discriminator=_digest(place))

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
        return _digest(" ".join(self.handle_parts))

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

    @property
    def label(self) -> str:
        """How this album is named to a reader, artist first.

        Stated once here because a finding is labelled with it and a screen
        offering to accept that finding has to name the same album back. Two
        spellings of one label read as two albums the moment either changes.
        """
        return f"{self.display_artist} - {self.display_title}"
