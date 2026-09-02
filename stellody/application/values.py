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
    # Audio this build recognises and cannot decode. Carried rather than
    # dropped, so a folder holding nothing else is still reported instead of
    # vanishing: a listener who cannot find an album they own has no way to
    # tell a format Stellody skipped from a library that failed to scan.
    unplayable: tuple[str, ...] = ()

    @property
    def signatures(self) -> dict[str, tuple[int, int]]:
        """Every audio file in this folder against its size and mtime.

        The unplayable ones are left out: nothing reads them, so they are not
        part of what a rescan compares. A folder holding only those has no
        signatures at all, which is what lets it be reused rather than
        re-listed at every scan.
        """
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


@dataclass(frozen=True, slots=True)
class ReleaseAsset:
    """One downloadable file offered by a published release."""

    name: str
    download_url: str


@dataclass(frozen=True, slots=True)
class ReleaseInfo:
    """A published release, as much of it as an update check needs."""

    version: str
    page_url: str
    assets: tuple[ReleaseAsset, ...] = ()


@dataclass(frozen=True, slots=True)
class UpdateStatus:
    """The answer to one update check, whatever that answer turns out to be.

    `latest` is empty when the question could not be asked at all, which is a
    different thing from being up to date and is reported differently.
    """

    current: str
    latest: str = ""
    update_available: bool = False
    download_url: str = ""
    page_url: str = ""

    @property
    def reached(self) -> bool:
        """Whether the release was read at all; False when nothing answered."""
        return bool(self.latest)
