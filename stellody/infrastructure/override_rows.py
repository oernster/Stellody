"""The rows behind accepted corrections.

Kept apart from the rest of the store because it is a concern of its own and
because the store had grown to the point where one more table's worth of SQL
would have pushed it into the band the line rule reserves for a real split.

Nothing here reaches a music file. An override is Stellody's own state, so it
lives in Stellody's own database beside the ratings and the settings, which is
the invariant the whole project exists for.
"""

from __future__ import annotations

import sqlite3

from stellody.domain.overrides import Override, OverrideField

# One pin per album, file and field, so accepting the same finding twice
# replaces rather than accumulates. The key is the same triple resolution looks
# a pin up by, so the table cannot hold a row the library would never read.
SCHEMA = """
CREATE TABLE IF NOT EXISTS overrides (
    album TEXT NOT NULL,
    path  TEXT NOT NULL DEFAULT '',
    field TEXT NOT NULL,
    value TEXT NOT NULL,
    PRIMARY KEY (album, path, field)
);
"""


def _field_of(stored: str) -> OverrideField | None:
    """The field a stored name stands for; None where it names none.

    A row naming a field this version does not know is skipped rather than
    raised over. Reading a library must not fail because an older or a newer
    Stellody wrote a row; a pin nobody can apply is simply not applied.
    """
    try:
        return OverrideField(stored)
    except ValueError:
        return None


def all_overrides(connection: sqlite3.Connection) -> tuple[Override, ...]:
    """Every accepted correction, in one read.

    The whole table at once, as the ratings are: it holds only what somebody
    has actually accepted; resolution needs all of it to assemble anything.
    """
    rows = connection.execute(
        "SELECT album, path, field, value FROM overrides ORDER BY album, path, field"
    ).fetchall()
    found: list[Override] = []
    for row in rows:
        field = _field_of(row["field"])
        if field is None:
            continue
        found.append(
            Override(
                album=row["album"], field=field, value=row["value"], path=row["path"]
            )
        )
    return tuple(found)


def accept(connection: sqlite3.Connection, accepted: tuple[Override, ...]) -> None:
    """Write pins, replacing any already standing for the same field.

    Written as one statement over the whole run rather than one a row, because
    accepting everything the report lists is the DEFAULT path through this
    feature rather than a power-user shortcut: on the reference library that is
    142 findings in one gesture.
    """
    if not accepted:
        return
    with connection:
        connection.executemany(
            "INSERT INTO overrides (album, path, field, value) VALUES (?, ?, ?, ?) "
            "ON CONFLICT(album, path, field) DO UPDATE SET value = excluded.value",
            [(item.album, item.path, str(item.field), item.value) for item in accepted],
        )


def discard(connection: sqlite3.Connection, unwanted: tuple[Override, ...]) -> None:
    """Drop pins by what they apply to, whatever value they were holding.

    The value is not part of the match: resetting is about which correction is
    being taken back, not about what it happened to say. Dropping a row lets the
    automatic rule show through again; the finding it answered comes back with
    it, because the raw tags were never altered.
    """
    if not unwanted:
        return
    with connection:
        connection.executemany(
            "DELETE FROM overrides WHERE album = ? AND path = ? AND field = ?",
            [(item.album, item.path, str(item.field)) for item in unwanted],
        )
