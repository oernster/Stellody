"""Recording which rules read a folder, in a database and in one written before.

A folder record is a reading of files rather than the files themselves, so what
read it has to travel with it. A library scanned before the question was asked
has no column to hold the answer, which is the case this covers.
"""

from __future__ import annotations

import pathlib
import sqlite3

import pytest

from stellody.application.values import FolderRecord
from stellody.infrastructure import folder_derivation
from stellody.infrastructure.store import SqliteLibraryStore

FOLDER = "H:/FLACMusic/Yoav/Charmed & Strange"
DERIVATION_READ_IT = 7


@pytest.fixture
def database(tmp_path: pathlib.Path) -> str:
    """Where one test's library lives."""
    return str(tmp_path / "library.db")


def test_what_read_a_folder_survives_being_written_and_read_back(
    database: str,
) -> None:
    store = SqliteLibraryStore(database)
    store.save_folder(FolderRecord(folder=FOLDER, derivation=DERIVATION_READ_IT))
    store.close()

    reopened = SqliteLibraryStore(database)
    try:
        held = reopened.load_folders()
    finally:
        reopened.close()
    assert [record.derivation for record in held] == [DERIVATION_READ_IT]


def test_a_folder_saying_nothing_about_its_rules_answers_to_no_rules(
    database: str,
) -> None:
    """Zero is what an older database carries; no rule set claims it."""
    store = SqliteLibraryStore(database)
    store.save_folder(FolderRecord(folder=FOLDER))
    store.close()

    reopened = SqliteLibraryStore(database)
    try:
        assert reopened.load_folders()[0].derivation == 0
    finally:
        reopened.close()


def _without_the_column(database: str) -> None:
    """Leave the folders table exactly as a database written earlier had it."""
    connection = sqlite3.connect(database)
    try:
        connection.execute("ALTER TABLE folders DROP COLUMN derivation")
        connection.commit()
    finally:
        connection.close()


def test_a_database_written_before_the_column_existed_gains_it(
    database: str,
) -> None:
    store = SqliteLibraryStore(database)
    store.close()
    _without_the_column(database)

    connection = sqlite3.connect(database)
    connection.row_factory = sqlite3.Row
    try:
        assert folder_derivation.ensure_column(connection) is True
        held = {row["name"] for row in connection.execute("PRAGMA table_info(folders)")}
    finally:
        connection.close()
    assert folder_derivation.COLUMN in held


def test_opening_such_a_database_can_read_its_folders_again(database: str) -> None:
    """The whole point: the store opens rather than failing on a missing column."""
    store = SqliteLibraryStore(database)
    store.save_folder(FolderRecord(folder=FOLDER, derivation=DERIVATION_READ_IT))
    store.close()
    _without_the_column(database)

    reopened = SqliteLibraryStore(database)
    try:
        held = reopened.load_folders()
    finally:
        reopened.close()
    assert [record.derivation for record in held] == [0]


def test_a_database_that_already_has_the_column_is_left_alone(database: str) -> None:
    store = SqliteLibraryStore(database)
    store.close()

    connection = sqlite3.connect(database)
    connection.row_factory = sqlite3.Row
    try:
        assert folder_derivation.ensure_column(connection) is False
    finally:
        connection.close()
