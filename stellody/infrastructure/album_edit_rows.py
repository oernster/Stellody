"""The rows behind an album's own description, as a listener has stated it.

Its own table rather than more columns on the corrections one, because the two
are keyed by different things and read at different moments. A correction is
keyed by an album's HANDLE and applied after the library is assembled; an album
edit is keyed by the FOLDER and applied before anything is folded, since it
changes what the album is identified by. Sharing a table would mean a column
that means one thing on some rows and another on the rest.

Nothing here reaches a music file. What somebody states about an album is
Stellody's own state, so it lives in Stellody's own database beside the ratings
and the settings, which is the invariant the whole project exists for.
"""

from __future__ import annotations

import sqlite3

from stellody.domain.overrides import AlbumEdit, AlbumField

# One value per folder and field, so stating a thing twice replaces rather than
# accumulates. The key is the pair assembly looks an edit up by, so the table
# cannot hold a row the library would never read.
SCHEMA = """
CREATE TABLE IF NOT EXISTS album_edits (
    folder TEXT NOT NULL,
    field  TEXT NOT NULL,
    value  TEXT NOT NULL,
    PRIMARY KEY (folder, field)
);
"""


def _field_of(stored: str) -> AlbumField | None:
    """The field a stored name stands for; None where it names none.

    A row naming a field this version does not know is skipped rather than
    raised over, for the reason the corrections table gives: reading a library
    must not fail because an older or a newer Stellody wrote a row.
    """
    try:
        return AlbumField(stored)
    except ValueError:
        return None


def all_album_edits(connection: sqlite3.Connection) -> tuple[AlbumEdit, ...]:
    """Everything anybody has stated about an album, in one read."""
    rows = connection.execute(
        "SELECT folder, field, value FROM album_edits ORDER BY folder, field"
    ).fetchall()
    found: list[AlbumEdit] = []
    for row in rows:
        field = _field_of(row["field"])
        if field is None or not row["value"]:
            continue
        found.append(AlbumEdit(folder=row["folder"], field=field, value=row["value"]))
    return tuple(found)


def state(connection: sqlite3.Connection, stated: tuple[AlbumEdit, ...]) -> None:
    """Write stated values, replacing any already standing for the same field."""
    if not stated:
        return
    with connection:
        connection.executemany(
            "INSERT INTO album_edits (folder, field, value) VALUES (?, ?, ?) "
            "ON CONFLICT(folder, field) DO UPDATE SET value = excluded.value",
            [(item.folder, str(item.field), item.value) for item in stated],
        )


def discard(connection: sqlite3.Connection, unwanted: tuple[AlbumEdit, ...]) -> None:
    """Drop stated values by what they apply to, whatever they were holding.

    The value is not part of the match: taking one back is about which
    statement is being withdrawn rather than about what it happened to say.
    An album whose stated description is dropped goes back to the one its tags
    give, which is what folded it before anybody said anything.
    """
    if not unwanted:
        return
    with connection:
        connection.executemany(
            "DELETE FROM album_edits WHERE folder = ? AND field = ?",
            [(item.folder, str(item.field)) for item in unwanted],
        )
