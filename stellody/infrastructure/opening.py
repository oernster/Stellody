"""Opening the library store, including when the file will not open at all.

The store holds two quite different things. The library index is a cache of
what a scan found, rebuildable from the music folder by a rescan. Everything
else in it is the listener's own and cannot be worked out again: settings,
every rating and play count, every accepted track correction and every album
edit. A rescan brings none of those back.

So a file that will not open is not a reason to refuse to start; neither is
it a cache to throw away. It is set aside whole, write ahead log and shared
memory file included, with a fresh one opened in its place: the application
comes up and says where the old file went and what is still in it. Refusing
to start instead leaves the user with a window that never appears and nothing
on screen to act on, which is what happened after a reinstall once a force
ended application had left its write ahead log behind.

The log goes WITH the file rather than being deleted. A committed row stays in
the log until a checkpoint copies it across; deleting the log discarded those
rows from the only copy left, so the set aside file opened without the most
recent ratings in it.
"""

from __future__ import annotations

import pathlib
import sqlite3

from stellody.infrastructure.store import SqliteLibraryStore

# What the sidecar files a live database keeps beside it are called. A set
# aside database takes its own with it, renamed to match its new name, so they
# are neither read against the fresh one nor lost: SQLite finds a database's
# log by appending the suffix to its name.
SIDECAR_SUFFIXES = ("-wal", "-shm")
SET_ASIDE_SUFFIX = ".damaged"


def set_aside_path(database: pathlib.Path) -> pathlib.Path:
    """Where a database that will not open goes, without overwriting the last.

    Numbered rather than stamped with the time: nothing here reads a clock,
    while the number says how many times this has happened, which is the more
    useful thing to know.
    """
    candidate = database.with_name(database.name + SET_ASIDE_SUFFIX)
    attempt = 1
    while candidate.exists():
        attempt += 1
        candidate = database.with_name(f"{database.name}{SET_ASIDE_SUFFIX}{attempt}")
    return candidate


def set_aside(database: pathlib.Path) -> pathlib.Path | None:
    """Move a database and its sidecars out of the way; None when it will not go.

    A sidecar that is not there is simply not moved. One that refuses to move
    does not undo the rest: the database itself is already out of the way,
    which is what lets the application start.
    """
    target = set_aside_path(database)
    try:
        database.replace(target)
    except OSError:
        return None
    for suffix in SIDECAR_SUFFIXES:
        sidecar = database.with_name(database.name + suffix)
        if not sidecar.exists():
            continue
        try:
            sidecar.replace(target.with_name(target.name + suffix))
        except OSError:
            continue
    return target


def open_store(
    database: pathlib.Path,
) -> tuple[SqliteLibraryStore, pathlib.Path | None]:
    """The store, plus where the old file went when it had to be set aside.

    A second failure is not caught. Once the damaged file is out of the way,
    anything still refusing to open is about the directory rather than the
    database; starting on a store that is not there would be worse than saying
    so.
    """
    try:
        return SqliteLibraryStore(str(database)), None
    except sqlite3.DatabaseError:
        moved = set_aside(database)
    return SqliteLibraryStore(str(database)), moved
