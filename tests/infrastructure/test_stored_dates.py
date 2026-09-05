"""Clearing padded dates out of a database written before the rule existed.

The scan reduces a date as it reads one, so these rows can only come from an
earlier run. An incremental scan will not revisit a folder nobody has touched,
so a store opened today has to settle them rather than wait.
"""

from __future__ import annotations

import pathlib
import sqlite3

import pytest

from stellody.infrastructure import stored_dates
from stellody.infrastructure.store import SqliteLibraryStore

FOLDER = "H:/FLACMusic/Yoav/Charmed & Strange"


@pytest.fixture
def connection(tmp_path: pathlib.Path) -> sqlite3.Connection:
    """A store's own database, opened again the way the cleaner sees it."""
    store = SqliteLibraryStore(str(tmp_path / "library.db"))
    store.close()
    opened = sqlite3.connect(str(tmp_path / "library.db"))
    opened.row_factory = sqlite3.Row
    return opened


def write_dates(connection: sqlite3.Connection, *dates: str) -> None:
    """Put one row in the sources table for each date given."""
    for index, date in enumerate(dates):
        connection.execute(
            "INSERT INTO sources (folder, path, file_name, start_frame, "
            "end_frame, duration_ms, sample_rate, bit_depth, album, "
            "album_artist, artists, title, date, genre, disc, track) VALUES "
            "(?, ?, ?, 0, 0, 0, 44100, 16, ?, ?, ?, ?, ?, ?, 1, ?)",
            (
                FOLDER,
                f"{FOLDER}/{index:02d} Track.m4a",
                f"{index:02d} Track.m4a",
                "Charmed & Strange",
                "Yoav",
                "Yoav",
                f"Track {index}",
                date,
                "Pop",
                index,
            ),
        )
    connection.commit()


def dates_in(connection: sqlite3.Connection) -> list[str]:
    rows = connection.execute("SELECT date FROM sources ORDER BY track").fetchall()
    return [row["date"] for row in rows]


def test_a_padded_date_loses_its_time(connection: sqlite3.Connection) -> None:
    write_dates(connection, "2007-10-09T12:00:00Z")
    assert stored_dates.clean(connection) == 1
    assert dates_in(connection) == ["2007-10-09"]


def test_every_row_holding_that_value_is_corrected(
    connection: sqlite3.Connection,
) -> None:
    """One statement covers the album, since a value is rewritten not a row."""
    write_dates(connection, *(["2007-10-09T12:00:00Z"] * 3))
    assert stored_dates.clean(connection) == 1
    assert dates_in(connection) == ["2007-10-09"] * 3


def test_the_four_placeholder_times_all_go(connection: sqlite3.Connection) -> None:
    """Measured: these are the only times of day the library carries."""
    write_dates(
        connection,
        "1990-05-01T12:00:00Z",
        "1991-05-01T07:00:00Z",
        "1992-05-01T08:00:00Z",
        "1993-05-01T00:00:00Z",
    )
    assert stored_dates.clean(connection) == 4
    assert dates_in(connection) == [
        "1990-05-01",
        "1991-05-01",
        "1992-05-01",
        "1993-05-01",
    ]


def test_a_date_already_reduced_is_left_alone(connection: sqlite3.Connection) -> None:
    """Every open after the first, which is why nothing is committed then."""
    write_dates(connection, "2011-05-02", "2001", "1989-04")
    assert stored_dates.clean(connection) == 0
    assert dates_in(connection) == ["2011-05-02", "2001", "1989-04"]


def test_a_shape_nobody_recognises_survives(connection: sqlite3.Connection) -> None:
    """Guessing at it would lose the only record of what the file said."""
    write_dates(connection, "Spring 1990")
    assert stored_dates.clean(connection) == 0
    assert dates_in(connection) == ["Spring 1990"]


def test_a_spaced_date_gains_its_dashes(connection: sqlite3.Connection) -> None:
    write_dates(connection, "2001 05 15")
    assert stored_dates.clean(connection) == 1
    assert dates_in(connection) == ["2001-05-15"]


def test_an_empty_date_is_not_asked_about(connection: sqlite3.Connection) -> None:
    """A file stating no date at all is not a value to reduce."""
    write_dates(connection, "", "2007-10-09T12:00:00Z")
    assert stored_dates.clean(connection) == 1
    assert dates_in(connection) == ["", "2007-10-09"]


def test_opening_a_store_cleans_what_it_finds(tmp_path: pathlib.Path) -> None:
    """The pass is wired into the open, so nothing has to remember to run it."""
    database = str(tmp_path / "library.db")
    store = SqliteLibraryStore(database)
    store.close()
    opened = sqlite3.connect(database)
    opened.row_factory = sqlite3.Row
    write_dates(opened, "2007-10-09T12:00:00Z")
    opened.close()
    reopened = SqliteLibraryStore(database)
    try:
        rows = reopened._connection.execute("SELECT date FROM sources").fetchall()
        assert [row["date"] for row in rows] == ["2007-10-09"]
    finally:
        reopened.close()
