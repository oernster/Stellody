"""Backups as zips: written, read and staged for the next start. BACKUP.md.

**The database is copied through SQLite's own backup, never as a file.** It runs
in write ahead mode, so the file alone can be missing whatever the log still
holds (FR-B08). The copy is taken on whichever thread asks, over a connection
of its own, since SQLite refuses one used from a thread that did not make it.

**The journals travel with their files.** The catalogue memory and the genre
cache are written whole only as Stellody quits; between those writes their
answers live in the running records beside them, so a backup without the
records silently loses that session. A record copied while a run appends to it
can end in a torn line, which the journal reader already skips.

**A backup is written under a temporary name and moved into place**, so a
failure leaves nothing that looks like a backup (FR-B12). A finished name is
never reused: the caller picks one nothing in the folder carries.

This module writes outside Stellody's own directory: into the one folder the
listener chose in a dialog, only ever a file of a fresh name. It reads nothing
there but the names already present.
"""

from __future__ import annotations

import hashlib
import json
import os
import pathlib
import shutil
import sqlite3
import tempfile
import zipfile
from collections.abc import Mapping
from datetime import UTC, datetime

from stellody.application.backing_up import BackupFailed, BackupRefused, Backups
from stellody.domain.backups import (
    BACKUP_FORMAT,
    Carried,
    Manifest,
    Refusal,
    RefusalKind,
    SchemaRange,
    Upgrade,
    restorable,
    schema_range,
    upgraded,
)
from stellody.infrastructure import (
    catalogue_memory,
    database_schema,
    discovery_file,
    paths,
    shop_file,
)
from stellody.infrastructure.atomic import PENDING_SUFFIX
from stellody.shared.version import __version__

# DATA-B01 bar the database: every JSON file a backup carries, against every
# step its owner has ever added. The database brings itself up as it opens
# (`database_schema.py`), so it needs none here.
UPGRADES: Mapping[str, tuple[Upgrade, ...]] = {
    catalogue_memory.MEMORY_NAME: catalogue_memory.MEMORY_UPGRADES,
    catalogue_memory.JOURNAL_NAME: catalogue_memory.JOURNAL_UPGRADES,
    discovery_file.DISCOVERY_NAME: discovery_file.DISCOVERY_UPGRADES,
    discovery_file.CACHE_NAME: discovery_file.CACHE_UPGRADES,
    discovery_file.CACHE_JOURNAL_NAME: discovery_file.CACHE_JOURNAL_UPGRADES,
    shop_file.SHOPS_NAME: shop_file.UPGRADES,
}
# DATA-B01: every file a backup carries, against the shapes it can be read in.
# Derived from the steps, so a range can never claim a shape no step reaches.
BACKED_UP: Mapping[str, SchemaRange] = {
    paths.DATABASE_NAME: database_schema.RANGE,
    **{name: schema_range(steps) for name, steps in UPGRADES.items()},
}
BACKUP_PREFIX = f"{paths.APP_DIR_SLUG}-backup"
SAFETY_PREFIX = f"{paths.APP_DIR_SLUG}-before-restore"
MANIFEST_NAME = "manifest.json"
# Where a confirmed restore waits inside Stellody's own directory, plus the
# note written into it last, which is what says the staging is complete.
STAGING_DIR = "restore-pending"
STAGED_NOTE = "restore.json"
BACKUP_KEY = "backup"
SAFETY_KEY = "safety"
NAMES_KEY = "names"
FORMAT_KEY = "format"
WRITTEN_BY_KEY = "written_by"
WRITTEN_KEY = "written"
FILES_KEY = "files"
NAME_KEY = "name"
SCHEMA_KEY = "schema"
CHECKSUM_KEY = "sha256"
# How much of a file is hashed or copied at a time, so a large database is
# never held whole in memory.
CHUNK_BYTES = 1 << 20


def _digest_of(stream) -> str:
    """The SHA-256 of everything this stream holds."""
    digest = hashlib.sha256()
    for chunk in iter(lambda: stream.read(CHUNK_BYTES), b""):
        digest.update(chunk)
    return digest.hexdigest()


def _database_copy(database: pathlib.Path, target: pathlib.Path) -> int:
    """Copy the live database through SQLite's backup; the schema it records."""
    source = sqlite3.connect(str(database))
    copy = sqlite3.connect(str(target))
    try:
        source.backup(copy)
        return database_schema.schema_of(copy)
    finally:
        copy.close()
        source.close()


def _manifest_from(raw: object) -> Manifest | None:
    """The manifest this parsed JSON describes; None where it describes none.

    **Every format ever written stays readable here** (FR-B38): a later format
    adds a branch for itself rather than changing what format 1 is read as.
    `tests/infrastructure/test_old_backups.py` holds a format 1 backup built
    from literal text, so renaming a key breaks a test rather than a backup.
    """
    try:
        carried = tuple(
            Carried(
                str(entry[NAME_KEY]), int(entry[SCHEMA_KEY]), str(entry[CHECKSUM_KEY])
            )
            for entry in raw[FILES_KEY]
        )
        return Manifest(
            format=int(raw[FORMAT_KEY]),
            written_by=str(raw[WRITTEN_BY_KEY]),
            written=datetime.fromisoformat(str(raw[WRITTEN_KEY])),
            carried=carried,
        )
    except (KeyError, TypeError, ValueError):
        return None


def _damaged(backup: str, detail: str) -> BackupRefused:
    """The refusal for a backup that is not intact."""
    return BackupRefused(
        Refusal(RefusalKind.DAMAGED, pathlib.Path(backup).name, detail=detail)
    )


class ZipArchive:
    """Backups written to, read from and staged out of zip files."""

    def __init__(
        self,
        data_dir: pathlib.Path,
        database: pathlib.Path,
        written_by: str,
        backed_up: Mapping[str, SchemaRange] = BACKED_UP,
        upgrades: Mapping[str, tuple[Upgrade, ...]] = UPGRADES,
    ) -> None:
        self._data_dir = data_dir
        self._database = database
        self._written_by = written_by
        self._backed_up = backed_up
        self._upgrades = upgrades

    def names_in(self, folder: str) -> frozenset[str]:
        """The names already in a folder; empty where it cannot be read."""
        try:
            return frozenset(entry.name for entry in pathlib.Path(folder).iterdir())
        except OSError:
            return frozenset()

    def write(self, folder: str, name: str, moment: datetime) -> str:
        """Write one backup into the folder; its full path. FR-B03, FR-B12."""
        final = pathlib.Path(folder) / name
        pending = final.with_name(final.name + PENDING_SUFFIX)
        try:
            with tempfile.TemporaryDirectory() as scratch:
                carried = self._zipped(pending, pathlib.Path(scratch))
                with zipfile.ZipFile(pending, "a") as zipped:
                    zipped.writestr(MANIFEST_NAME, self._manifest(moment, carried))
            os.replace(pending, final)
        except (OSError, sqlite3.Error, zipfile.BadZipFile) as error:
            pending.unlink(missing_ok=True)
            raise BackupFailed(
                f"The backup could not be written to {pathlib.Path(folder)}: {error}"
            ) from error
        return str(final)

    def _zipped(self, pending: pathlib.Path, scratch: pathlib.Path) -> list[Carried]:
        """Put every file of the set that exists into a new zip. FR-B09, FR-B10."""
        carried: list[Carried] = []
        with zipfile.ZipFile(pending, "w", zipfile.ZIP_DEFLATED) as zipped:
            for name, understood in self._backed_up.items():
                if name == paths.DATABASE_NAME:
                    if not self._database.exists():
                        continue
                    copy = scratch / name
                    schema = _database_copy(self._database, copy)
                    with copy.open("rb") as stream:
                        checksum = _digest_of(stream)
                    zipped.write(copy, name)
                else:
                    try:
                        content = (self._data_dir / name).read_bytes()
                    except FileNotFoundError:
                        continue
                    schema = understood.newest
                    checksum = hashlib.sha256(content).hexdigest()
                    zipped.writestr(name, content)
                carried.append(Carried(name, schema, checksum))
        return carried

    def _manifest(self, moment: datetime, carried: list[Carried]) -> str:
        """The manifest naming the format, the writer and every file. FR-B14."""
        return json.dumps(
            {
                FORMAT_KEY: BACKUP_FORMAT,
                WRITTEN_BY_KEY: self._written_by,
                WRITTEN_KEY: moment.isoformat(),
                FILES_KEY: [
                    {
                        NAME_KEY: item.name,
                        SCHEMA_KEY: item.schema,
                        CHECKSUM_KEY: item.checksum,
                    }
                    for item in carried
                ],
            }
        )

    def read(self, backup: str) -> Manifest:
        """The manifest of a backup whose every listed file is intact. FR-B28."""
        try:
            with zipfile.ZipFile(backup) as zipped:
                try:
                    raw = json.loads(zipped.read(MANIFEST_NAME))
                except (KeyError, ValueError):
                    raise _damaged(backup, "it holds no readable manifest") from None
                manifest = _manifest_from(raw)
                if manifest is None:
                    raise _damaged(backup, "its manifest is not one this version reads")
                present = set(zipped.namelist())
                for carried in manifest.carried:
                    if carried.name not in present:
                        raise _damaged(backup, f"{carried.name} is missing from it")
                    with zipped.open(carried.name) as stream:
                        if _digest_of(stream) != carried.checksum:
                            raise _damaged(backup, f"{carried.name} fails its checksum")
        except (OSError, zipfile.BadZipFile):
            raise _damaged(backup, "it is not a backup this version can open") from None
        return manifest

    def stage(self, backup: str, safety: str) -> None:
        """Unpack a backup to replace the live set at the next start. FR-B23.

        The note is written last: a staging without one was interrupted, so
        the next start discards it rather than putting half a backup in place.
        """
        staging = self._data_dir / STAGING_DIR
        try:
            shutil.rmtree(staging, ignore_errors=True)
            staging.mkdir(parents=True)
            names = self._unpacked(backup, staging)
            (staging / STAGED_NOTE).write_text(
                json.dumps({BACKUP_KEY: backup, SAFETY_KEY: safety, NAMES_KEY: names}),
                encoding="utf-8",
            )
        # ValueError is an upgrade step that could not read what it was given.
        except (OSError, ValueError, zipfile.BadZipFile, BackupRefused) as error:
            shutil.rmtree(staging, ignore_errors=True)
            raise BackupFailed(
                f"The backup could not be made ready to restore: {error}"
            ) from error

    def _unpacked(self, backup: str, staging: pathlib.Path) -> list[str]:
        """Copy every restorable file out of the backup, checking each again.

        A JSON file written at an older schema is taken up to the newest on
        the way out, through every step its owner added since (FR-B30). The
        database is copied as it is: the store brings it up as it opens.
        """
        manifest = self.read(backup)
        names: list[str] = []
        with zipfile.ZipFile(backup) as zipped:
            for carried in restorable(manifest, self._backed_up):
                target = staging / carried.name
                steps = self._upgrades.get(carried.name)
                if steps is None:
                    with zipped.open(carried.name) as source, target.open("wb") as out:
                        shutil.copyfileobj(source, out, CHUNK_BYTES)
                else:
                    understood = self._backed_up[carried.name]
                    target.write_bytes(
                        upgraded(
                            zipped.read(carried.name), carried.schema, understood, steps
                        )
                    )
                names.append(carried.name)
        return names


def backups() -> Backups:
    """The backup and restore errands over Stellody's own directory."""
    return Backups(
        ZipArchive(paths.data_dir(), paths.database_path(), __version__),
        BACKED_UP,
        BACKUP_PREFIX,
        SAFETY_PREFIX,
        _local_now,
    )


def _local_now() -> datetime:
    """This moment on the listener's own clock, which is what a name shows."""
    return datetime.now(UTC).astimezone()
