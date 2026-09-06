"""The values that cross a port: what the world hands back and what it takes.

Kept apart from `ports.py` so that file holds interfaces alone, which is what
its name says. A record here knows nothing about where it came from or what
will be done with it; that is the whole reason it can be handed between a
layer that reads a disk and one that must never touch one.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum

from stellody.domain.discovery import Gaps
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


class RunOutcome(StrEnum):
    """How a discovery run ended, which decides whether it has anything to say.

    Four endings rather than two, because "nothing was written" covers three
    quite different things and a listener is owed which one it was.
    """

    COMPLETED = "completed"
    NOTHING_TO_ASK = "nothing-to-ask"
    CANCELLED = "cancelled"
    UNAVAILABLE = "unavailable"


@dataclass(frozen=True, slots=True)
class DiscoveryProgress:
    """How far a run has got, named rather than merely counted.

    A run over a whole library takes about eleven minutes at the rate the
    catalogues permit, so a bar with no name against it is indistinguishable
    from a hang.
    """

    artist: str
    done: int
    total: int


@dataclass(frozen=True, slots=True)
class Ambiguity:
    """An artist whose name reached more than one artist in the catalogue.

    Reported rather than guessed at: choosing between two bands of one name on
    somebody's behalf files a whole discography under the wrong heading, and
    does it silently.
    """

    artist: str
    identifiers: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class SourceFailure:
    """An artist a catalogue could not answer about, with what it said."""

    artist: str
    reason: str


@dataclass(frozen=True, slots=True)
class RunReport:
    """Everything one discovery run found, including what it could not.

    The failures are carried beside the results rather than logged and
    forgotten, because an artist nobody could look up is exactly the artist
    somebody would otherwise assume had nothing missing.
    """

    outcome: RunOutcome
    gaps: tuple[Gaps, ...] = ()
    unresolved: tuple[str, ...] = ()
    ambiguous: tuple[Ambiguity, ...] = ()
    failed: tuple[SourceFailure, ...] = ()

    @property
    def is_writable(self) -> bool:
        """Whether this run has anything to replace the discovery file with.

        Only a completed run does. A cancelled one discards what it gathered,
        an unavailable one never gathered anything and a run with nobody to ask
        about has nothing to say that a file could carry.
        """
        return self.outcome is RunOutcome.COMPLETED
