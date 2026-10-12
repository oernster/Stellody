"""The backup and restore errands, over an archive standing in. BACKUP.md."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from stellody.application.backing_up import BackupFailed, BackupRefused, Backups
from stellody.domain.backups import (
    BACKUP_FORMAT,
    Carried,
    Manifest,
    RefusalKind,
    SchemaRange,
)

MOMENT = datetime(2026, 10, 12, 14, 5, tzinfo=UTC)
KNOWN = {"library.sqlite3": SchemaRange(0, 1)}


class StandingArchive:
    """Records what it was asked; holds a manifest; can be told to fail."""

    def __init__(self, manifest: Manifest | None = None, refuse_in: str = "") -> None:
        self.manifest = manifest
        self.refuse_in = refuse_in
        self.taken: frozenset[str] = frozenset()
        self.written: list[tuple[str, str]] = []
        self.staged: list[tuple[str, str]] = []
        self.read_from: list[str] = []

    def names_in(self, folder: str) -> frozenset[str]:
        return self.taken

    def write(self, folder: str, name: str, moment: datetime) -> str:
        if folder == self.refuse_in:
            raise BackupFailed(f"Could not write to {folder}: refused")
        self.written.append((folder, name))
        return f"{folder}/{name}"

    def read(self, backup: str) -> Manifest:
        self.read_from.append(backup)
        assert self.manifest is not None
        return self.manifest

    def stage(self, backup: str, safety: str) -> None:
        self.staged.append((backup, safety))


def _service(archive: StandingArchive) -> Backups:
    return Backups(archive, KNOWN, "app-backup", "app-before-restore", lambda: MOMENT)


def _manifest(schema: int) -> Manifest:
    carried = (Carried("library.sqlite3", schema, "0" * 64),)
    return Manifest(BACKUP_FORMAT, "1.0.0", MOMENT, carried)


def test_a_backup_is_written_under_a_dated_name() -> None:
    """FR-B03."""
    archive = StandingArchive()
    written = _service(archive).back_up("D:/Backups")
    assert archive.written == [("D:/Backups", "app-backup-2026-10-12-1405.zip")]
    assert written == "D:/Backups/app-backup-2026-10-12-1405.zip"


def test_a_name_already_in_the_folder_is_not_reused() -> None:
    """FR-B04."""
    archive = StandingArchive()
    archive.taken = frozenset({"app-backup-2026-10-12-1405.zip"})
    _service(archive).back_up("D:/Backups")
    assert archive.written[0][1] == "app-backup-2026-10-12-1405-2.zip"


def test_verification_comes_before_confirmation() -> None:
    """FR-B27: a restorable backup answers its manifest."""
    manifest = _manifest(1)
    archive = StandingArchive(manifest)
    assert _service(archive).verify("x.zip") is manifest
    assert archive.staged == [], "checking stages nothing"


def test_a_newer_schema_is_refused() -> None:
    """FR-B29."""
    archive = StandingArchive(_manifest(2))
    with pytest.raises(BackupRefused) as raised:
        _service(archive).verify("x.zip")
    assert raised.value.refusal.kind is RefusalKind.NEWER_SCHEMA
    assert "schema 2" in str(raised.value)


def test_the_safety_backup_comes_first() -> None:
    """FR-B20: written under its own prefix before anything is staged."""
    archive = StandingArchive()
    safety = _service(archive).restore("x.zip", "D:/Backups")
    assert archive.written == [("D:/Backups", "app-before-restore-2026-10-12-1405.zip")]
    assert archive.staged == [("x.zip", safety)]


def test_a_failed_safety_backup_stops_the_restore() -> None:
    """FR-B21."""
    archive = StandingArchive(refuse_in="D:/Backups")
    with pytest.raises(BackupFailed):
        _service(archive).restore("x.zip", "D:/Backups")
    assert archive.staged == []
