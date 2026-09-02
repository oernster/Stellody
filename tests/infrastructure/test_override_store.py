"""Accepted corrections kept in the real store, across a real restart.

The milestone promises that an accepted correction survives a restart and a
rescan, so these close the database and open it again rather than reading back
from the connection that wrote it. A store holding a value only until the
process ends would pass every other test here.
"""

from __future__ import annotations

import pathlib
import sqlite3

from stellody.domain.overrides import Override, OverrideField
from stellody.infrastructure.store import SqliteLibraryStore

ALBUM = "0123456789abcdef"
OTHER_ALBUM = "fedcba9876543210"
FIRST = "H:/Music/Portishead/Dummy/01 Mysterons.flac"
SECOND = "H:/Music/Portishead/Dummy/02 Sour Times.flac"


def _database(tmp_path: pathlib.Path) -> str:
    return str(tmp_path / "library.db")


def _reopened(database: str) -> SqliteLibraryStore:
    """The same file, opened afresh, which is what a restart really does."""
    return SqliteLibraryStore(database)


def test_a_fresh_store_has_accepted_nothing(tmp_path: pathlib.Path) -> None:
    store = SqliteLibraryStore(_database(tmp_path))
    try:
        assert store.all_overrides() == ()
    finally:
        store.close()


def test_an_accepted_correction_survives_a_restart(tmp_path: pathlib.Path) -> None:
    """The whole of what this milestone promises, asked of the file itself."""
    database = _database(tmp_path)
    store = SqliteLibraryStore(database)
    try:
        store.accept_overrides(
            (Override(ALBUM, OverrideField.TRACK_NUMBER, "3", FIRST),)
        )
    finally:
        store.close()

    store = _reopened(database)
    try:
        assert store.all_overrides() == (
            Override(ALBUM, OverrideField.TRACK_NUMBER, "3", FIRST),
        )
    finally:
        store.close()


def test_an_album_wide_pin_keeps_its_empty_path(tmp_path: pathlib.Path) -> None:
    database = _database(tmp_path)
    store = SqliteLibraryStore(database)
    try:
        store.accept_overrides(
            (Override(ALBUM, OverrideField.ALBUM_ARTIST, "Portishead"),)
        )
    finally:
        store.close()

    store = _reopened(database)
    try:
        held = store.all_overrides()
        assert held[0].path == ""
        assert held[0].value == "Portishead"
    finally:
        store.close()


def test_accepting_the_same_field_twice_replaces_rather_than_accumulates(
    tmp_path: pathlib.Path,
) -> None:
    """One pin per album, file and field, which the key is what enforces."""
    store = SqliteLibraryStore(_database(tmp_path))
    try:
        store.accept_overrides((Override(ALBUM, OverrideField.TITLE, "Early", FIRST),))
        store.accept_overrides((Override(ALBUM, OverrideField.TITLE, "Late", FIRST),))
        held = store.all_overrides()
        assert len(held) == 1
        assert held[0].value == "Late"
    finally:
        store.close()


def test_a_whole_report_is_accepted_in_one_gesture(tmp_path: pathlib.Path) -> None:
    """Accepting everything is the default path, so it is one write not many."""
    store = SqliteLibraryStore(_database(tmp_path))
    try:
        store.accept_overrides(
            tuple(
                Override(
                    ALBUM, OverrideField.TRACK_NUMBER, str(number), f"{FIRST}{number}"
                )
                for number in range(50)
            )
        )
        assert len(store.all_overrides()) == 50
    finally:
        store.close()


def test_discarding_takes_a_correction_back(tmp_path: pathlib.Path) -> None:
    database = _database(tmp_path)
    store = SqliteLibraryStore(database)
    try:
        store.accept_overrides((Override(ALBUM, OverrideField.TITLE, "Mine", FIRST),))
        store.discard_overrides((Override(ALBUM, OverrideField.TITLE, "Mine", FIRST),))
    finally:
        store.close()

    store = _reopened(database)
    try:
        assert store.all_overrides() == ()
    finally:
        store.close()


def test_what_a_pin_said_is_no_part_of_taking_it_back(tmp_path: pathlib.Path) -> None:
    """Resetting is about which correction, never about what it happened to say."""
    store = SqliteLibraryStore(_database(tmp_path))
    try:
        store.accept_overrides(
            (Override(ALBUM, OverrideField.TITLE, "What was stored", FIRST),)
        )
        store.discard_overrides(
            (Override(ALBUM, OverrideField.TITLE, "Something else", FIRST),)
        )
        assert store.all_overrides() == ()
    finally:
        store.close()


def test_discarding_one_leaves_the_others(tmp_path: pathlib.Path) -> None:
    store = SqliteLibraryStore(_database(tmp_path))
    try:
        store.accept_overrides(
            (
                Override(ALBUM, OverrideField.TITLE, "One", FIRST),
                Override(ALBUM, OverrideField.TITLE, "Two", SECOND),
                Override(OTHER_ALBUM, OverrideField.TITLE, "Three", FIRST),
            )
        )
        store.discard_overrides((Override(ALBUM, OverrideField.TITLE, "One", FIRST),))
        held = store.all_overrides()
        assert {(item.album, item.path) for item in held} == {
            (ALBUM, SECOND),
            (OTHER_ALBUM, FIRST),
        }
    finally:
        store.close()


def test_accepting_nothing_writes_nothing(tmp_path: pathlib.Path) -> None:
    store = SqliteLibraryStore(_database(tmp_path))
    try:
        store.accept_overrides(())
        assert store.all_overrides() == ()
    finally:
        store.close()


def test_discarding_nothing_leaves_everything(tmp_path: pathlib.Path) -> None:
    store = SqliteLibraryStore(_database(tmp_path))
    try:
        store.accept_overrides((Override(ALBUM, OverrideField.TITLE, "Mine", FIRST),))
        store.discard_overrides(())
        assert len(store.all_overrides()) == 1
    finally:
        store.close()


def test_a_row_naming_an_unknown_field_is_skipped_rather_than_raised_over(
    tmp_path: pathlib.Path,
) -> None:
    """An older or a newer Stellody must not cost this one its library.

    Written straight into the table, since nothing in this version can produce
    such a row; a pin nobody can apply is simply not applied.
    """
    database = _database(tmp_path)
    store = SqliteLibraryStore(database)
    try:
        store.accept_overrides(
            (Override(ALBUM, OverrideField.TITLE, "Readable", FIRST),)
        )
    finally:
        store.close()

    planted = sqlite3.connect(database)
    with planted:
        planted.execute(
            "INSERT INTO overrides (album, path, field, value) VALUES (?, ?, ?, ?)",
            (ALBUM, SECOND, "a-field-from-the-future", "whatever"),
        )
    planted.close()

    store = _reopened(database)
    try:
        held = store.all_overrides()
        assert len(held) == 1
        assert held[0].value == "Readable"
    finally:
        store.close()
