"""Every file a backup carries knows its shape. BACKUP.md FR-B15 to FR-B17."""

from __future__ import annotations

import sqlite3

from stellody.infrastructure import database_schema, paths
from stellody.infrastructure.backup_file import BACKED_UP
from stellody.infrastructure.store import SqliteLibraryStore

# DATA-B01, stated here as the specification states it.
DATA_B01 = {
    "library.sqlite3",
    "catalogue-memory.json",
    "catalogue-memory.record",
    "discovered.json",
    "candidate-genres-2.json",
    "candidate-genres-2.record",
    "shops.json",
}
# A folders table as libraries had it before the derivation column existed.
OLD_FOLDERS = (
    "CREATE TABLE folders (folder TEXT PRIMARY KEY, "
    "art_path TEXT NOT NULL DEFAULT '', has_embedded_art INTEGER NOT NULL DEFAULT 0)"
)


def _schema_of(database) -> int:
    connection = sqlite3.connect(database)
    try:
        return database_schema.schema_of(connection)
    finally:
        connection.close()


def test_the_database_carries_its_number(tmp_path) -> None:
    """FR-B15."""
    database = tmp_path / paths.DATABASE_NAME
    SqliteLibraryStore(str(database)).close()
    assert _schema_of(database) == database_schema.NEWEST


def test_an_unnumbered_library_is_brought_up(tmp_path) -> None:
    """FR-B16: the column arrives and the number is recorded."""
    database = tmp_path / paths.DATABASE_NAME
    connection = sqlite3.connect(database)
    connection.execute(OLD_FOLDERS)
    connection.execute("INSERT INTO folders (folder) VALUES ('D:/Music/A')")
    connection.commit()
    connection.close()
    store = SqliteLibraryStore(str(database))
    try:
        columns = {
            row["name"]
            for row in store._connection.execute("PRAGMA table_info(folders)")
        }
        assert "derivation" in columns
        assert [record.folder for record in store.load_folders()] == ["D:/Music/A"]
    finally:
        store.close()
    assert _schema_of(database) == database_schema.NEWEST


def test_a_newer_library_is_left_as_it_is(tmp_path) -> None:
    """A newer release's library is not this one's to change."""
    database = tmp_path / paths.DATABASE_NAME
    SqliteLibraryStore(str(database)).close()
    newer = database_schema.NEWEST + 1
    connection = sqlite3.connect(database)
    connection.execute(f"PRAGMA user_version = {newer}")
    connection.commit()
    connection.close()
    SqliteLibraryStore(str(database)).close()
    assert _schema_of(database) == newer


def test_every_owner_declares_its_range() -> None:
    """FR-B17: every file of the set has a range, the newest at least the oldest."""
    assert set(BACKED_UP) == DATA_B01
    for name, understood in BACKED_UP.items():
        assert 0 <= understood.oldest <= understood.newest, name
