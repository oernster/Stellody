"""The values that cross a port: what the world hands back and what it takes.

Kept apart from `ports.py` so that file holds interfaces alone, which is what
its name says. A record here knows nothing about where it came from or what
will be done with it; that is the whole reason it can be handed between a
layer that reads a disk and one that must never touch one.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field

from stellody.domain.health import LibraryIssue
from stellody.domain.ordering import TrackCandidate
from stellody.domain.track import TrackSource


@dataclass(frozen=True, slots=True)
class FileStat:
    """What the filesystem says about one audio file, without opening it."""

    path: str
    file_name: str
    size: int
    mtime: int

    @property
    def signature(self) -> tuple[int, int]:
        """The pair compared to decide whether a file needs reprobing."""
        return (self.size, self.mtime)


@dataclass(frozen=True, slots=True)
class FolderListing:
    """One folder of a music library, as the walker found it."""

    folder: str
    audio: tuple[FileStat, ...]
    cue_paths: tuple[str, ...] = ()
    image_paths: tuple[str, ...] = ()

    @property
    def signatures(self) -> dict[str, tuple[int, int]]:
        """Every audio file in this folder against its size and mtime."""
        return {item.path: item.signature for item in self.audio}


@dataclass(frozen=True, slots=True)
class AudioProperties:
    """What a probe reads out of one audio file. Read only, always."""

    sample_rate: int
    bit_depth: int
    frame_count: int
    has_embedded_art: bool = False
    tags: Mapping[str, tuple[str, ...]] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class SourceRecord:
    """One playable source as persisted: raw tag values, not resolved ones.

    Resolution rules live in the domain and are applied on load, so improving
    them takes effect without rescanning a library.
    """

    path: str
    file_name: str
    start_frame: int = 0
    end_frame: int | None = None
    duration_ms: int = 0
    sample_rate: int = 0
    bit_depth: int = 0
    album: str = ""
    album_artist: str = ""
    artists: tuple[str, ...] = ()
    title: str = ""
    date: str = ""
    genre: str = ""
    disc: int | None = None
    track: int | None = None

    @property
    def track_source(self) -> TrackSource:
        """The domain source this record addresses."""
        return TrackSource(
            path=self.path,
            start_frame=self.start_frame,
            end_frame=self.end_frame,
        )

    @property
    def candidate(self) -> TrackCandidate:
        """This record as the domain's adjudication input."""
        return TrackCandidate(
            file_name=self.file_name,
            source=self.track_source,
            duration_ms=self.duration_ms,
            sample_rate=self.sample_rate,
            bit_depth=self.bit_depth,
            tag_disc=self.disc,
            tag_track=self.track,
            tag_title=self.title,
            artists=self.artists,
        )


@dataclass(frozen=True, slots=True)
class FolderRecord:
    """A whole folder's scan result, the unit the store caches."""

    folder: str
    stats: tuple[FileStat, ...] = ()
    sources: tuple[SourceRecord, ...] = ()
    art_path: str = ""
    has_embedded_art: bool = False
    issues: tuple[LibraryIssue, ...] = ()

    @property
    def signatures(self) -> dict[str, tuple[int, int]]:
        """Every audio file recorded here against its size and mtime."""
        return {item.path: item.signature for item in self.stats}
