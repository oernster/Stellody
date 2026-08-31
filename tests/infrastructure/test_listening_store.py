"""A rating and a play count kept in the real store, across a real restart.

The point of the milestone is that these survive, so the test closes the
database and opens it again rather than reading back from the connection that
wrote it. A store that holds a value only until the process ends would pass
every other test here.
"""

from __future__ import annotations

import pathlib

from stellody.domain.listening import Listening
from stellody.infrastructure.store import SqliteLibraryStore

TRACK = "0123456789abcdef"
OTHER = "fedcba9876543210"
PATH = "01 Mars.flac"


def _database(tmp_path: pathlib.Path) -> str:
    return str(tmp_path / "library.db")


def test_a_fresh_store_holds_nothing(tmp_path: pathlib.Path) -> None:
    store = SqliteLibraryStore(_database(tmp_path))
    try:
        assert store.all_listening() == {}
    finally:
        store.close()


def test_a_rating_survives_a_restart(tmp_path: pathlib.Path) -> None:
    """The whole of what this milestone promises, asked of the file itself."""
    database = _database(tmp_path)
    store = SqliteLibraryStore(database)
    store.set_listening(TRACK, PATH, Listening(stars=4, plays=2))
    store.close()
    reopened = SqliteLibraryStore(database)
    try:
        assert reopened.all_listening() == {TRACK: Listening(stars=4, plays=2)}
    finally:
        reopened.close()


def test_writing_the_same_track_again_replaces_it(tmp_path: pathlib.Path) -> None:
    store = SqliteLibraryStore(_database(tmp_path))
    try:
        store.set_listening(TRACK, PATH, Listening(stars=1))
        store.set_listening(TRACK, PATH, Listening(stars=5, plays=1))
        assert store.all_listening() == {TRACK: Listening(stars=5, plays=1)}
    finally:
        store.close()


def test_two_tracks_are_kept_apart(tmp_path: pathlib.Path) -> None:
    store = SqliteLibraryStore(_database(tmp_path))
    try:
        store.set_listening(TRACK, PATH, Listening(stars=3))
        store.set_listening(OTHER, "02 Venus.flac", Listening(plays=9))
        assert store.all_listening() == {
            TRACK: Listening(stars=3),
            OTHER: Listening(plays=9),
        }
    finally:
        store.close()


def test_an_existing_database_gains_the_table(tmp_path: pathlib.Path) -> None:
    """Opening a library written before any of this existed must not fail.

    The schema is applied on every open, so a database from an earlier version
    gains the table rather than needing a migration written by hand.
    """
    database = _database(tmp_path)
    first = SqliteLibraryStore(database)
    first._connection.execute("DROP TABLE listening")
    first._connection.commit()
    first.close()
    reopened = SqliteLibraryStore(database)
    try:
        reopened.set_listening(TRACK, PATH, Listening(stars=2))
        assert reopened.all_listening()[TRACK].stars == 2
    finally:
        reopened.close()
