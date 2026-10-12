"""The library database's shape, numbered. BACKUP.md FR-B15, FR-B16.

Measured on 2026-10-12: no library database recorded which shape it was in, so
nothing could compare one copy with another. SQLite keeps a whole number in
every file for exactly this (`PRAGMA user_version`), zero until somebody sets
it; every library written before this module is therefore schema zero.

**Each step takes the database up by one; every step runs on every open.**
Each must therefore be safe on a file that already has what it adds, which is
also what lets a library written before numbering arrive in whatever shape a
past release left it. Running them all rather than only those above the
recorded number keeps the store repairing a file whose number and shape
disagree, as it did before numbers existed
(`tests/infrastructure/test_folder_derivation.py`); each step is one cheap
question when there is nothing to do. The newest schema is the number of
steps, so adding a step is the only way to change it.

A database numbered above the newest step is left as it is. That is a newer
release's library opened by an older one; changing it would be guessing.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Callable

from stellody.domain.backups import SchemaRange
from stellody.infrastructure import folder_derivation

# Every step in order; step n takes schema n to schema n + 1.
STEPS: tuple[Callable[[sqlite3.Connection], object], ...] = (
    # Schema 1: the column saying how each folder was read.
    folder_derivation.ensure_column,
)
NEWEST = len(STEPS)
# A file written before numbering is still read, by taking it up every step.
OLDEST = 0
RANGE = SchemaRange(OLDEST, NEWEST)


def schema_of(connection: sqlite3.Connection) -> int:
    """The schema number the open database records."""
    return int(connection.execute("PRAGMA user_version").fetchone()[0])


def bring_up(connection: sqlite3.Connection) -> int:
    """Apply every step, then record the number; the number it was found at."""
    found = schema_of(connection)
    if found > NEWEST:
        return found
    for step in STEPS:
        step(connection)
    if found < NEWEST:
        # PRAGMA takes no bound parameter; the number is this module's own.
        connection.execute(f"PRAGMA user_version = {NEWEST}")
        connection.commit()
    return found
