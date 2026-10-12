"""A staged restore put in place by the next start. BACKUP.md FR-B24 to B26, B34."""

from __future__ import annotations

import json
import pathlib
import sqlite3

from backup_support import MOMENT, archive, data_folder, setting_in

from stellody.infrastructure import database_schema, paths, staged_restore
from stellody.infrastructure.backup_file import STAGED_NOTE, STAGING_DIR
from stellody.infrastructure.staged_restore import ASIDE_DIR
from stellody.infrastructure.store import SqliteLibraryStore

NAME = "app-backup-2026-10-12-1405.zip"


def _staged(tmp_path: pathlib.Path, setting: str = "from the backup") -> pathlib.Path:
    """A backup of one library staged over another; the live data folder."""
    source = data_folder(tmp_path / "source", setting)
    out = tmp_path / "out"
    out.mkdir()
    written = archive(source).write(str(out), NAME, MOMENT)
    live = data_folder(tmp_path / "live", "the current one")
    archive(live).stage(written, "safety.zip")
    return live


def test_nothing_staged_is_nothing_done(tmp_path) -> None:
    assert staged_restore.apply(tmp_path) is None


def test_the_next_start_completes_it(tmp_path) -> None:
    """FR-B24: the restored set is live; no staging remains."""
    live = _staged(tmp_path)
    restored = staged_restore.apply(live)
    assert restored is not None and restored.failure == ""
    assert restored.backup.endswith(NAME) and restored.safety == "safety.zip"
    assert setting_in(live / paths.DATABASE_NAME) == "from the backup"
    assert not (live / STAGING_DIR).exists()
    assert not (live / ASIDE_DIR).exists()


def test_a_file_the_backup_lacks_is_removed(tmp_path) -> None:
    """FR-B25: a restore replaces; it does not merge."""
    live = _staged(tmp_path)
    (live / "shops.json").write_text("{}", encoding="utf-8")
    staged_restore.apply(live)
    assert not (live / "shops.json").exists()


def test_an_old_wal_is_not_replayed(tmp_path) -> None:
    """FR-B26: the sidecars from before go aside with the database."""
    live = _staged(tmp_path)
    (live / (paths.DATABASE_NAME + "-wal")).write_bytes(b"pages of the old library")
    staged_restore.apply(live)
    assert not (live / (paths.DATABASE_NAME + "-wal")).exists()
    assert setting_in(live / paths.DATABASE_NAME) == "from the backup"


def test_an_older_database_is_brought_up(tmp_path) -> None:
    """FR-B30: a schema zero library opens at the current schema, rows intact."""
    live = _staged(tmp_path)
    database = live / STAGING_DIR / paths.DATABASE_NAME
    connection = sqlite3.connect(database)
    connection.execute("PRAGMA user_version = 0")
    connection.commit()
    connection.close()
    staged_restore.apply(live)
    store = SqliteLibraryStore(str(live / paths.DATABASE_NAME))
    try:
        assert store.get_setting("probe") == "from the backup"
        assert database_schema.schema_of(store._connection) == database_schema.NEWEST
    finally:
        store.close()


def test_a_failure_part_way_is_undone(tmp_path) -> None:
    """FR-B34: the old set is whole again and the failure is reported."""
    live = _staged(tmp_path)
    note_path = live / STAGING_DIR / STAGED_NOTE
    note = json.loads(note_path.read_text(encoding="utf-8"))
    note["names"].append("shops.json")
    note_path.write_text(json.dumps(note), encoding="utf-8")
    restored = staged_restore.apply(live)
    assert restored is not None and restored.failure
    assert setting_in(live / paths.DATABASE_NAME) == "the current one"
    assert not (live / STAGING_DIR).exists()


def test_an_interrupted_staging_is_discarded(tmp_path) -> None:
    """A staging with no note was never finished; half a backup is not put in."""
    live = _staged(tmp_path)
    (live / STAGING_DIR / STAGED_NOTE).unlink()
    assert staged_restore.apply(live) is None
    assert not (live / STAGING_DIR).exists()
    assert setting_in(live / paths.DATABASE_NAME) == "the current one"


def test_a_note_that_is_not_an_object_counts_as_none(tmp_path) -> None:
    live = _staged(tmp_path)
    (live / STAGING_DIR / STAGED_NOTE).write_text("[]", encoding="utf-8")
    assert staged_restore.apply(live) is None
