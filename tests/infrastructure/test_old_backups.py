"""Old backups stay restorable. BACKUP.md FR-B30, FR-B37, FR-B38.

Oliver's ruling, 2026-10-12: a backup made by an older Stellody must restore.

The first backup here is built from LITERAL text, never from the module's
constants: it is what format 1 looks like on somebody's disk today. Renaming a
key, changing a name or dropping a reader for format 1 has to fail here rather
than on the day a listener needs their old backup back. Never edit it to make a
change pass; a new format is a new test beside it.
"""

from __future__ import annotations

import hashlib
import json
import pathlib
import sqlite3
import zipfile

import pytest
from backup_support import MOMENT, archive, data_folder, setting_in

from stellody.application.backing_up import BackupFailed
from stellody.domain.backups import FIRST_SCHEMA, schema_range
from stellody.infrastructure import database_schema, paths, staged_restore
from stellody.infrastructure.backup_file import (
    BACKED_UP,
    STAGING_DIR,
    UPGRADES,
    ZipArchive,
)
from stellody.infrastructure.store import SqliteLibraryStore

# What every owner could read on the day its shape was first numbered. FR-B37:
# an owner may add shapes but never stop reading one of these.
FIRST_READABLE = {name: FIRST_SCHEMA for name in UPGRADES} | {
    "library.sqlite3": 0,
}


def _format_one(folder: pathlib.Path, database: pathlib.Path) -> pathlib.Path:
    """A format 1 backup as written to disk, its manifest typed out in full."""
    library = database.read_bytes()
    shops = b'{"shops": []}'
    manifest = {
        "format": 1,
        "written_by": "0.1.0",
        "written": "2026-10-12T14:05:00+01:00",
        "files": [
            {
                "name": "library.sqlite3",
                "schema": 0,
                "sha256": hashlib.sha256(library).hexdigest(),
            },
            {
                "name": "shops.json",
                "schema": 1,
                "sha256": hashlib.sha256(shops).hexdigest(),
            },
        ],
    }
    backup = folder / "stellody-backup-2026-10-12-1405.zip"
    with zipfile.ZipFile(backup, "w") as zipped:
        zipped.writestr("library.sqlite3", library)
        zipped.writestr("shops.json", shops)
        zipped.writestr("manifest.json", json.dumps(manifest))
    return backup


def _unnumbered_library(where: pathlib.Path) -> pathlib.Path:
    """A library from before schema numbers existed: user_version zero."""
    database = where / "old.sqlite3"
    store = SqliteLibraryStore(str(database))
    store.set_setting("probe", "from an old backup")
    store.close()
    connection = sqlite3.connect(database)
    connection.execute("PRAGMA user_version = 0")
    connection.execute("PRAGMA journal_mode = DELETE")
    connection.commit()
    connection.close()
    return database


def test_a_format_one_backup_of_an_unnumbered_library_restores(tmp_path) -> None:
    """FR-B38 then FR-B30, end to end: read, staged, put in place, opened."""
    live = data_folder(tmp_path / "live", "the current one")
    backup = _format_one(tmp_path, _unnumbered_library(tmp_path))
    manifest = archive(live).read(str(backup))
    assert manifest.format == 1
    archive(live).stage(str(backup), "safety.zip")
    assert staged_restore.apply(live).failure == ""
    assert setting_in(live / paths.DATABASE_NAME) == "from an old backup"
    store = SqliteLibraryStore(str(live / paths.DATABASE_NAME))
    try:
        assert database_schema.schema_of(store._connection) == database_schema.NEWEST
    finally:
        store.close()
    assert (live / "shops.json").read_bytes() == b'{"shops": []}'


def test_no_owner_stops_reading_a_shape_it_once_wrote() -> None:
    """FR-B37: every range still starts where it started."""
    assert {name: held.oldest for name, held in BACKED_UP.items()} == FIRST_READABLE


def test_a_file_from_before_a_change_is_brought_up_as_it_is_staged(
    tmp_path,
) -> None:
    """FR-B30 for a JSON file: an owner that has added a step since."""
    data = data_folder(tmp_path)
    out = tmp_path / "out"
    out.mkdir()
    (data / "shops.json").write_bytes(b"v1")
    written = archive(data).write(str(out), "a.zip", MOMENT)
    steps = (lambda held: held + b"+v2",)
    later = ZipArchive(
        data,
        data / paths.DATABASE_NAME,
        "later",
        backed_up={**BACKED_UP, "shops.json": schema_range(steps)},
        upgrades={"shops.json": steps},
    )
    later.stage(written, "safety.zip")
    assert (data / STAGING_DIR / "shops.json").read_bytes() == b"v1+v2"


def test_a_step_that_cannot_read_its_file_stages_nothing(tmp_path) -> None:
    data = data_folder(tmp_path)
    out = tmp_path / "out"
    out.mkdir()
    (data / "shops.json").write_bytes(b"v1")
    written = archive(data).write(str(out), "a.zip", MOMENT)

    def unreadable(held: bytes) -> bytes:
        raise ValueError("not the shape this step expects")

    later = ZipArchive(
        data,
        data / paths.DATABASE_NAME,
        "later",
        backed_up={**BACKED_UP, "shops.json": schema_range((unreadable,))},
        upgrades={"shops.json": (unreadable,)},
    )
    with pytest.raises(BackupFailed) as raised:
        later.stage(written, "safety.zip")
    assert "not the shape" in str(raised.value)
    assert not (data / STAGING_DIR).exists()
