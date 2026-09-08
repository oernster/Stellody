"""Giving an older database the column that says how its folders were read.

`CREATE TABLE IF NOT EXISTS` leaves a table that already exists exactly as it
is, so a column added to the schema reaches new databases alone. Every library
scanned before this arrived has a `folders` table without it; the first
read of that column would fail outright rather than report an old reading.

So it is added here where it is missing, defaulting to zero. No set of rules
answers to zero, which is precisely what marks every folder in such a database
as needing to be read again.

The music files are not involved. This changes the shape of what Stellody
wrote down, never what it read.
"""

from __future__ import annotations

import sqlite3

TABLE = "folders"
COLUMN = "derivation"


def ensure_column(connection: sqlite3.Connection) -> bool:
    """Add the derivation column where it is missing; whether it was added."""
    held = {row["name"] for row in connection.execute(f"PRAGMA table_info({TABLE})")}
    if COLUMN in held:
        return False
    connection.execute(
        f"ALTER TABLE {TABLE} ADD COLUMN {COLUMN} INTEGER NOT NULL DEFAULT 0"
    )
    connection.commit()
    return True
