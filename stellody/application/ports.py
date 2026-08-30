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
from stellody.domain.playback import (
    OutputReport,
    OutputRequest,
    PlaybackPosition,
    PlaybackState,
)
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

    def count(self, root: str) -> int:
        """How many folders the walk will yield, counted without reading one.

        A scan cannot say how far through it is without knowing how far there
        is to go; the walk itself only knows that once it has finished.
        """
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


class SettingsStore(Protocol):
    """Small persistent preferences: appearance, library root, close behaviour."""

    def get_setting(self, key: str, default: str = "") -> str:
        """The stored value for a key; the default when it has never been set."""
        ...

    def set_setting(self, key: str, value: str) -> None:
        """Store a value against a key."""
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


class ClosableStore(LibraryStore, Protocol):
    """A store that holds a handle of its own and must give it back.

    The scan opens its own store on its own thread, so something has to close
    it when the thread is done.
    """

    def close(self) -> None:
        """Release the handle."""
        ...


class PlaybackPort(Protocol):
    """Turns a track source into sound. The only thing that touches a device.

    Every method is safe to call in any state, so the application never has to
    guard a transport command with a state check.
    """

    @property
    def state(self) -> PlaybackState:
        """Where the transport is right now."""
        ...

    def load(self, source: TrackSource, request: OutputRequest) -> OutputReport:
        """Open `source` on a device and report what was actually opened.

        Stops whatever was playing first. Raises when the source cannot be
        decoded at all; a device refusing the requested mode is a fallback
        recorded in the report, not an error.
        """
        ...

    def play(self) -> None:
        """Start or resume. Does nothing when no source is loaded."""
        ...

    def pause(self) -> None:
        """Hold position without releasing the device."""
        ...

    def stop(self) -> None:
        """End playback and release the device."""
        ...

    def seek(self, frame: int) -> None:
        """Move to a frame offset within the loaded source, clamped to it."""
        ...

    def position(self) -> PlaybackPosition | None:
        """How far the DECODE has reached; None when nothing is loaded.

        This runs ahead of what is coming out of the speakers, by whatever is
        sitting in the buffer. Use `Transport.position` for a figure fit to
        show somebody.
        """
        ...

    @property
    def lead_frames(self) -> int:
        """How far the decode runs ahead of what is audible, in frames.

        A property of the device the port opened rather than of the track, so
        the port is the only thing that can answer it.
        """
        ...

    @property
    def finished(self) -> bool:
        """Whether the loaded source has played all the way through.

        A track reaching its end is not a state the transport is in, it is an
        event nothing was told about: the device is still open and the position
        has simply stopped moving. Something has to ask.
        """
        ...

    def set_volume(self, level: float) -> None:
        """Set output gain, where 0.0 is silence and 1.0 is unattenuated."""
        ...

    def close(self) -> None:
        """Release every resource. The port is unusable afterwards."""
        ...
