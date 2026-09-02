"""What one scan changed about a library, as a comparison of two readings.

A scan already reports how much work it did: folders probed, folders reused,
files read. None of that answers the question somebody actually presses Rescan
to ask, which is what turned up. So this compares the library as it stood
against the library as it stands and says what is different.

Kept in the domain because it is a rule rather than a display. What counts as a
new album, then what counts as a new track, are decisions that should be made in
one place and testable with nothing installed.
"""

from __future__ import annotations

from dataclasses import dataclass

from stellody.domain.album import Album
from stellody.domain.identity import AlbumIdentity


@dataclass(frozen=True, slots=True)
class LibraryChange:
    """The difference between two readings of one library.

    `previous_albums` is carried rather than derived because an empty library
    before the scan and a scan that happened to find nothing new are different
    answers; only the first should be described as a first reading.
    """

    new_albums: tuple[AlbumIdentity, ...] = ()
    gone_albums: tuple[AlbumIdentity, ...] = ()
    new_tracks: int = 0
    gone_tracks: int = 0
    total_albums: int = 0
    total_tracks: int = 0
    previous_albums: int = 0

    def __post_init__(self) -> None:
        for name in ("new_tracks", "gone_tracks", "total_albums", "total_tracks"):
            if getattr(self, name) < 0:
                raise ValueError(f"{name} cannot be negative")
        if self.previous_albums < 0:
            raise ValueError("previous_albums cannot be negative")

    @property
    def is_first_reading(self) -> bool:
        """True when there was no library before this scan."""
        return self.previous_albums == 0

    @property
    def nothing_changed(self) -> bool:
        """True when the scan found the library exactly as it left it."""
        return not (
            self.new_albums or self.gone_albums or self.new_tracks or self.gone_tracks
        )


def _identities(albums: tuple[Album, ...]) -> dict[AlbumIdentity, Album]:
    return {album.identity: album for album in albums}


def _sources(albums: tuple[Album, ...]) -> set[object]:
    """Every distinct piece of audio in a library.

    A track is keyed by its source rather than by its title or its position,
    since a source survives a retag while both of the others can be rewritten
    by one. A cue-sheet album shares one file across its tracks, so the slice
    is part of the key and not merely the path.
    """
    return {track.source for album in albums for track in album.tracks}


def compare_libraries(
    before: tuple[Album, ...], after: tuple[Album, ...]
) -> LibraryChange:
    """What changed between two readings, ordered as the library orders itself.

    An album is new when its identity was not there before. That identity is
    built from tags, so retagging an album can read as one album leaving and
    another arriving; both halves are reported rather than the arrival alone,
    since a report naming only what appeared would describe a rename as a
    discovery.
    """
    was = _identities(before)
    now = _identities(after)
    before_sources = _sources(before)
    after_sources = _sources(after)
    return LibraryChange(
        new_albums=tuple(
            sorted(
                (identity for identity in now if identity not in was),
                key=lambda identity: identity.sort_key,
            )
        ),
        gone_albums=tuple(
            sorted(
                (identity for identity in was if identity not in now),
                key=lambda identity: identity.sort_key,
            )
        ),
        new_tracks=len(after_sources - before_sources),
        gone_tracks=len(before_sources - after_sources),
        total_albums=len(after),
        total_tracks=sum(album.track_count for album in after),
        previous_albums=len(before),
    )
