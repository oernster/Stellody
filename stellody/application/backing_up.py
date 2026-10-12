"""Backing the library up, checking a backup, putting one back. BACKUP.md.

Three entry points, one per thing a listener can ask for or that asking leads
to: write a backup into a folder; check a chosen backup before anybody is asked
to confirm (FR-B27); stage a confirmed one, having first saved what is there
now (FR-B20). The restore itself completes at the next start, before the
library is opened (FR-B24), which is not this module's business.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from datetime import datetime
from typing import Protocol

from stellody.domain.backups import (
    BACKUP_FORMAT,
    Manifest,
    Refusal,
    SchemaRange,
    backup_name,
    judged,
)


class BackupFailed(Exception):
    """A backup could not be written; else a restore could not be staged.

    The message names the folder and the reason, since a full disk and a folder
    that refuses writes need different things doing about them. FR-B12.
    """


class BackupRefused(Exception):
    """A chosen backup cannot be restored. FR-B28, FR-B29, FR-B31."""

    def __init__(self, refusal: Refusal) -> None:
        super().__init__(refusal.sentence)
        self.refusal = refusal


class BackupArchive(Protocol):
    """Where backups are written, read and staged."""

    def names_in(self, folder: str) -> frozenset[str]:
        """The file names already in a folder; empty where it cannot be read."""
        ...

    def write(self, folder: str, name: str, moment: datetime) -> str:
        """Write a backup; its full path. Raises BackupFailed."""
        ...

    def read(self, backup: str) -> Manifest:
        """The manifest of a backup whose every file is present and intact.

        Raises BackupRefused naming the damage otherwise.
        """
        ...

    def stage(self, backup: str, safety: str) -> None:
        """Unpack a backup to replace the live set at the next start.

        Raises BackupFailed.
        """
        ...


class Backups:
    """The backup and restore errands, over an archive."""

    def __init__(
        self,
        archive: BackupArchive,
        known: Mapping[str, SchemaRange],
        prefix: str,
        safety_prefix: str,
        now: Callable[[], datetime],
    ) -> None:
        self._archive = archive
        self._known = known
        self._prefix = prefix
        self._safety_prefix = safety_prefix
        self._now = now

    def back_up(self, folder: str) -> str:
        """Write a backup into this folder; its full path. FR-B03."""
        return self._written(self._prefix, folder)

    def verify(self, backup: str) -> Manifest:
        """What a backup holds, once it is known it can be restored. FR-B27."""
        manifest = self._archive.read(backup)
        refusal = judged(manifest, self._known, BACKUP_FORMAT)
        if refusal is not None:
            raise BackupRefused(refusal)
        return manifest

    def restore(self, backup: str, safety_folder: str) -> str:
        """Save what is there now, then stage the backup; the safety backup.

        Nothing is staged unless the safety backup was written: a failure
        there raises before the archive is asked to stage anything. FR-B21.
        """
        safety = self._written(self._safety_prefix, safety_folder)
        self._archive.stage(backup, safety)
        return safety

    def _written(self, prefix: str, folder: str) -> str:
        """Write one backup under this prefix, named so nothing is replaced."""
        moment = self._now()
        name = backup_name(prefix, moment, self._archive.names_in(folder))
        return self._archive.write(folder, name, moment)
