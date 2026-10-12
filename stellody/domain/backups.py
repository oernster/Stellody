"""What a backup is, plus whether one may be restored. BACKUP.md.

A backup is judged by the shape of each file it carries, never by the version
of Stellody that wrote it (Oliver's ruling, 2026-10-12): two releases can share
a shape, while one release can change several. Each file has an owner that
declares the oldest shape it can still read and the newest it writes; a file
outside that range cannot be put back, since the owner cannot know what it
means.

Nothing here reads a file, a clock or a zip. The moment a backup is named for
arrives as an argument; the files arrive already listed.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

# The shape every owner started numbering from. A file written before numbers
# existed is schema zero, which is below it.
FIRST_SCHEMA = 1
# The layout of the zip and its manifest, as distinct from any file's shape.
BACKUP_FORMAT = 1
# The minute a backup is named for, so two on one day do not share a name.
NAME_STAMP = "%Y-%m-%d-%H%M"
ZIP_SUFFIX = ".zip"
# Where a second backup inside one minute starts counting. The first carries
# no number at all, so the second is the first to need one.
SECOND = 2


@dataclass(frozen=True, slots=True)
class SchemaRange:
    """The shapes one owner understands: the oldest it reads, the newest it writes."""

    oldest: int
    newest: int

    def __post_init__(self) -> None:
        if self.oldest < 0 or self.oldest > self.newest:
            raise ValueError(
                f"no schema range runs from {self.oldest} to {self.newest}"
            )


@dataclass(frozen=True, slots=True)
class Carried:
    """One file inside a backup: its name, its shape and its checksum."""

    name: str
    schema: int
    checksum: str


@dataclass(frozen=True, slots=True)
class Manifest:
    """What a backup says about itself. FR-B14."""

    format: int
    written_by: str
    written: datetime
    carried: tuple[Carried, ...]


class RefusalKind(StrEnum):
    """Why a backup cannot be put back."""

    DAMAGED = "damaged"
    NEWER_FORMAT = "newer format"
    NEWER_SCHEMA = "newer schema"
    OLDER_SCHEMA = "older schema"


@dataclass(frozen=True, slots=True)
class Refusal:
    """A backup refused, naming what was wrong with it. FR-B28, FR-B29, FR-B31."""

    kind: RefusalKind
    name: str
    found: int = 0
    limit: int = 0
    detail: str = ""

    @property
    def sentence(self) -> str:
        """What the listener is told, naming the file and both numbers."""
        if self.kind is RefusalKind.DAMAGED:
            return f"{self.name} cannot be restored: {self.detail}."
        if self.kind is RefusalKind.NEWER_FORMAT:
            return (
                f"{self.name} was written in backup format {self.found}; this "
                f"version reads format {self.limit} at most. A newer version "
                "can restore it."
            )
        if self.kind is RefusalKind.NEWER_SCHEMA:
            return (
                f"The backup holds {self.name} at schema {self.found}; this "
                f"version understands schema {self.limit} at most. A newer "
                "version can restore it."
            )
        return (
            f"The backup holds {self.name} at schema {self.found}; this version "
            f"reads schema {self.limit} at the oldest."
        )


def judged(
    manifest: Manifest, known: Mapping[str, SchemaRange], newest_format: int
) -> Refusal | None:
    """The reason this backup cannot be restored; None when it can.

    A file the backup holds that no owner here knows is not a reason: a cache
    renamed for a rule change is a new name, so an older backup carries the old
    one, which nothing would read. It is left out rather than refused.
    """
    if manifest.format > newest_format:
        return Refusal(
            RefusalKind.NEWER_FORMAT, "This backup", manifest.format, newest_format
        )
    for carried in manifest.carried:
        understood = known.get(carried.name)
        if understood is None:
            continue
        if carried.schema > understood.newest:
            return Refusal(
                RefusalKind.NEWER_SCHEMA,
                carried.name,
                carried.schema,
                understood.newest,
            )
        if carried.schema < understood.oldest:
            return Refusal(
                RefusalKind.OLDER_SCHEMA,
                carried.name,
                carried.schema,
                understood.oldest,
            )
    return None


def restorable(
    manifest: Manifest, known: Mapping[str, SchemaRange]
) -> tuple[Carried, ...]:
    """The files of this backup an owner here will take back."""
    return tuple(carried for carried in manifest.carried if carried.name in known)


def backup_name(prefix: str, moment: datetime, taken: frozenset[str]) -> str:
    """The file a backup made at this moment is written to. FR-B03, FR-B04.

    A name already in the folder gains a counter rather than being replaced:
    two backups inside one minute are possible, losing the first is not.
    """
    stem = f"{prefix}-{moment.strftime(NAME_STAMP)}"
    name = stem + ZIP_SUFFIX
    count = SECOND
    while name in taken:
        name = f"{stem}-{count}{ZIP_SUFFIX}"
        count += 1
    return name
