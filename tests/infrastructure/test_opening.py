"""Opening the store when the file will not open at all.

Measured after a reinstall: the application died on startup with "database
disk image is malformed" and showed nothing, because the store was opened
where nothing could catch it. Setting the file aside whole and starting is
better than refusing to start; whole, because it also holds the ratings, play
counts, corrections and album edits a rescan cannot rebuild.
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
    """Moved beside the set aside file under its name, never deleted.

    They used to be deleted, which threw away every committed row the write
    ahead log had not yet handed back to the main file: ratings, play counts
    and corrections among them. Asserted on the move itself rather than
    through open_store, since the fresh store opening afterwards writes its
    own sidecars under the old names.
    """
    database = tmp_path / "library.sqlite3"
    database.write_bytes(b"not a database at all")
    for suffix in opening.SIDECAR_SUFFIXES:
        database.with_name(database.name + suffix).write_bytes(suffix.encode())
    target = opening.set_aside(database)
    assert target == tmp_path / "library.sqlite3.damaged"
    for suffix in opening.SIDECAR_SUFFIXES:
        assert not database.with_name(database.name + suffix).exists()
        moved = target.with_name(target.name + suffix)
        assert moved.read_bytes() == suffix.encode(), "kept beside the copy"


def a_row_only_the_log_holds(folder: pathlib.Path) -> pathlib.Path:
    """A database whose one rating row lives in its write ahead log alone.

    The writer is never closed or checkpointed while the files are copied,
    which is the state a force ended application leaves behind. The copy is
    what is returned; the writer is closed afterwards, against the original.
    """
    live = folder / "live"
    live.mkdir()
    writer = sqlite3.connect(live / "library.sqlite3")
    writer.execute("PRAGMA journal_mode=WAL")
    writer.execute("PRAGMA wal_autocheckpoint=0")
    writer.execute("CREATE TABLE listening (handle TEXT PRIMARY KEY, stars INT)")
    writer.commit()
    writer.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    writer.execute("INSERT INTO listening VALUES ('track', 5)")
    writer.commit()
    copied = folder / "library.sqlite3"
    try:
        for suffix in ("", *opening.SIDECAR_SUFFIXES):
            name = "library.sqlite3" + suffix
            (folder / name).write_bytes((live / name).read_bytes())
    finally:
        writer.close()
    return copied


def stars_in(database: pathlib.Path) -> list[tuple[str, int]]:
    """What a fresh reader finds in the listening table of this file."""
    reader = sqlite3.connect(database)
    try:
        return reader.execute("SELECT handle, stars FROM listening").fetchall()
    finally:
        reader.close()


def test_a_set_aside_copy_still_holds_what_only_its_log_held(
    tmp_path: pathlib.Path,
) -> None:
    """Measured: the row is in the log and nowhere else, then survives the move."""
    database = a_row_only_the_log_holds(tmp_path)
    main_alone = tmp_path / "alone" / "library.sqlite3"
    main_alone.parent.mkdir()
    main_alone.write_bytes(database.read_bytes())
    assert stars_in(main_alone) == [], "the main file alone lacks the row"
    target = opening.set_aside(database)
    assert target is not None
    assert stars_in(target) == [("track", 5)]


def test_a_sidecar_that_will_not_go_does_not_stop_the_rest(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The database is already out of the way, which is the part that matters."""
    database = tmp_path / "library.sqlite3"
    database.write_bytes(b"not a database at all")
    for suffix in opening.SIDECAR_SUFFIXES:
        database.with_name(database.name + suffix).write_bytes(b"held")
    real_replace = pathlib.Path.replace

    def refuse_sidecars(self: pathlib.Path, target: pathlib.Path) -> pathlib.Path:
        if self.name.endswith(opening.SIDECAR_SUFFIXES):
            raise OSError("in use")
        return real_replace(self, target)

    monkeypatch.setattr(pathlib.Path, "replace", refuse_sidecars)
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
