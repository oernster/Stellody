"""Opening the library store, including when the file will not open at all.

The store holds two quite different things. The library index is a cache of
what a scan found, rebuildable from the music folder in seconds. The settings
beside it are the only part that cannot be worked out again; they are a
handful of short rows.

So a file that will not open is not a reason to refuse to start. It is set
aside whole, with a fresh one opened in its place: the application comes up,
says what happened and offers a rescan. Refusing to start instead leaves the
user with a window that never appears and nothing on screen to act on, which
is what happened after a reinstall once a force ended application had left its
write ahead log behind.
"""

from __future__ import annotations

import pathlib
import sqlite3

from stellody.infrastructure.store import SqliteLibraryStore

# What the sidecar files a live database keeps beside it are called, so a set
# aside database takes its own with it rather than leaving them to be read
# against the fresh one.
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
    """Move a database and its sidecars out of the way; None when it will not go."""
    target = set_aside_path(database)
    try:
        database.replace(target)
    except OSError:
        return None
    for suffix in SIDECAR_SUFFIXES:
        sidecar = database.with_name(database.name + suffix)
        try:
            sidecar.unlink(missing_ok=True)
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
