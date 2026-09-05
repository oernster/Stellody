"""Clearing the padding out of dates this database was given earlier.

A date tag written by the iTunes store carries a time that names nothing: the
release day wearing noon UTC, else one of two spellings of midnight in US
Pacific. Measured across the reference library, every file holding a time held
one of those four and not one carried a real offset.

The scan now reduces a date as it reads it, so nothing arriving from here on
holds a time. Rows written before that do; they stay wrong until the folder
they came from happens to be read again. A library is scanned incrementally, so
for a folder nobody touches that is never.

So this runs once when the database is opened and settles the question rather
than waiting on it. It reads the distinct dates alone rather than the rows, so
a library of thousands of files asks about a few dozen values; where every one
is already reduced, which is every open after the first, it writes nothing.

The music files are not involved. This changes what Stellody wrote down, never
what it read.
"""

from __future__ import annotations

import sqlite3

from stellody.domain.text import tag_date


def clean(connection: sqlite3.Connection) -> int:
    """Reduce every stored date to the day it names; how many values changed.

    Returns a count of DISTINCT values rewritten rather than of rows, since
    that is what says whether there was anything to do.
    """
    rows = connection.execute(
        "SELECT DISTINCT date FROM sources WHERE date <> ''"
    ).fetchall()
    changed = 0
    for row in rows:
        stored = row["date"]
        reduced = tag_date(stored)
        if reduced == stored:
            continue
        connection.execute(
            "UPDATE sources SET date = ? WHERE date = ?", (reduced, stored)
        )
        changed += 1
    if changed:
        connection.commit()
    return changed
