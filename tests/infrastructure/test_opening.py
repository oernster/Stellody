"""Opening the store when the file will not open at all.

Measured after a reinstall: the application died on startup with "database
disk image is malformed" and showed nothing, because the store was opened
where nothing could catch it. The index is a cache of what a scan found, so
setting it aside and starting is better than refusing to start.
"""

from __future__ import annotations

import pathlib
import sqlite3

import pytest

from stellody.infrastructure import opening
from stellody.infrastructure.store import SqliteLibraryStore


def a_real_store(path: pathlib.Path) -> None:
    """One store written and closed, so the file is a genuine database."""
    store = SqliteLibraryStore(str(path))
    store.set_setting("theme", "dark")
    store.close()


def test_a_healthy_database_is_opened_and_left_where_it_is(
    tmp_path: pathlib.Path,
) -> None:
    database = tmp_path / "library.sqlite3"
    a_real_store(database)
    store, set_aside = opening.open_store(database)
    try:
        assert set_aside is None
        assert store.get_setting("theme", "") == "dark"
    finally:
        store.close()


def test_a_file_that_will_not_open_is_set_aside_and_a_fresh_one_takes_over(
    tmp_path: pathlib.Path,
) -> None:
    database = tmp_path / "library.sqlite3"
    database.write_bytes(b"not a database at all")
    store, set_aside = opening.open_store(database)
    try:
        assert set_aside == tmp_path / "library.sqlite3.damaged"
        assert set_aside.read_bytes() == b"not a database at all", "kept whole"
        assert store.get_setting("theme", "unset") == "unset", "a fresh one"
    finally:
        store.close()


def test_setting_a_database_aside_takes_its_sidecars_with_it(
    tmp_path: pathlib.Path,
) -> None:
    """A write ahead log read against a different database is its own fault.

    Asserted on the move itself rather than through open_store, since the
    fresh store opening afterwards replaces those files anyway: a test that
    went the long way round passed whether or not this removed anything.
    """
    database = tmp_path / "library.sqlite3"
    database.write_bytes(b"not a database at all")
    for suffix in opening.SIDECAR_SUFFIXES:
        database.with_name(database.name + suffix).write_bytes(b"stale")
    assert opening.set_aside(database) == tmp_path / "library.sqlite3.damaged"
    for suffix in opening.SIDECAR_SUFFIXES:
        assert not database.with_name(database.name + suffix).exists()


def test_a_sidecar_that_will_not_go_does_not_stop_the_rest(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The database is already out of the way, which is the part that matters."""
    database = tmp_path / "library.sqlite3"
    database.write_bytes(b"not a database at all")

    def refuse(*_: object, **__: object) -> None:
        raise OSError("in use")

    monkeypatch.setattr(pathlib.Path, "unlink", refuse)
    assert opening.set_aside(database) == tmp_path / "library.sqlite3.damaged"


def test_a_second_damaged_file_does_not_overwrite_the_first(
    tmp_path: pathlib.Path,
) -> None:
    database = tmp_path / "library.sqlite3"
    database.write_bytes(b"first")
    opening.open_store(database)[0].close()
    database.unlink()
    database.write_bytes(b"second")
    store, set_aside = opening.open_store(database)
    store.close()
    assert set_aside == tmp_path / "library.sqlite3.damaged2"
    assert (tmp_path / "library.sqlite3.damaged").read_bytes() == b"first"


def test_a_file_that_will_not_move_is_reported_rather_than_hidden(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Then the trouble is the directory; saying so beats pretending."""
    database = tmp_path / "library.sqlite3"
    database.write_bytes(b"not a database at all")

    def refuse(*_: object, **__: object) -> None:
        raise OSError("in use")

    monkeypatch.setattr(pathlib.Path, "replace", refuse)
    with pytest.raises(sqlite3.DatabaseError):
        opening.open_store(database)
