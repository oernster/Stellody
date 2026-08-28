"""Ports: the interfaces the application layer needs the world to satisfy.

Every one is a Protocol, so infrastructure satisfies it structurally and the
test suite can supply a hand-written fake without a mocking library.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from typing import Protocol

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


class LibraryWalker(Protocol):
    """Finds the folders of a music library. Never opens an audio file."""

    def walk(self, root: str) -> Iterable[FolderListing]:
        """Yield one listing per folder containing audio."""
        ...


class MediaProbe(Protocol):
    """Reads properties and tags out of one audio file."""

    def read(self, path: str) -> AudioProperties | None:
        """Properties of the file; None when it cannot be read."""
        ...


class TextReader(Protocol):
    """Reads a small text file, such as a cue sheet."""

    def read(self, path: str) -> str | None:
        """The file's text; None when it cannot be read."""
        ...


class LibraryStore(Protocol):
    """Stellody's own persistent state. The only thing it ever writes."""

    def file_signatures(self) -> Mapping[str, tuple[int, int]]:
        """Every known audio file against its recorded size and mtime."""
        ...

    def load_folders(self) -> tuple[FolderRecord, ...]:
        """Every folder record currently held."""
        ...

    def save_folder(self, record: FolderRecord) -> None:
        """Replace one folder's record with a freshly scanned one."""
        ...

    def mark_absent(self, seen_paths: frozenset[str]) -> int:
        """Flag files no longer on disk. Never deletes their metadata."""
        ...
