"""The rows a folder record is assembled from and taken apart into.

Kept apart from the rest of the store for the reason `override_rows` was: it is
a concern of its own; adding the column that says which rules read a folder
pushed the store into the band the line rule reserves for a real split.

A folder is stored as four tables rather than one row, since the files, the
sources and the findings are each many to its one. Reading them is what lives
here; deciding what to do with them stays with the store.

Nothing here reaches a music file. These are Stellody's own notes about a
library, never the library itself.
"""

from __future__ import annotations

import sqlite3

from stellody.application.values import FileStat, SourceRecord
from stellody.domain.health import IssueKind, LibraryIssue

UNIT_SEPARATOR = "\x1f"

SOURCE_COLUMNS = (
    "path, file_name, start_frame, end_frame, duration_ms, sample_rate, "
    "bit_depth, album, album_artist, artists, title, date, genre, disc, track"
)


def join(values: tuple[str, ...]) -> str:
    """Pack a tuple of strings into one column."""
    return UNIT_SEPARATOR.join(values)


def split(value: str) -> tuple[str, ...]:
    """Unpack a column written by join."""
    return tuple(part for part in value.split(UNIT_SEPARATOR) if part)


def stats_of(connection: sqlite3.Connection, folder: str) -> tuple[FileStat, ...]:
    """The recorded file statistics for one folder."""
    rows = connection.execute(
        "SELECT path, file_name, size, mtime FROM files "
        "WHERE folder = ? ORDER BY file_name",
        (folder,),
    )
    return tuple(
        FileStat(
            path=row["path"],
            file_name=row["file_name"],
            size=row["size"],
            mtime=row["mtime"],
        )
        for row in rows
    )


def sources_of(connection: sqlite3.Connection, folder: str) -> tuple[SourceRecord, ...]:
    """The stored sources for one folder, tags exactly as they were read."""
    rows = connection.execute(
        f"SELECT {SOURCE_COLUMNS} FROM sources "
        "WHERE folder = ? ORDER BY file_name, start_frame",
        (folder,),
    )
    return tuple(
        SourceRecord(
            path=row["path"],
            file_name=row["file_name"],
            start_frame=row["start_frame"],
            end_frame=row["end_frame"],
            duration_ms=row["duration_ms"],
            sample_rate=row["sample_rate"],
            bit_depth=row["bit_depth"],
            album=row["album"],
            album_artist=row["album_artist"],
            artists=split(row["artists"]),
            title=row["title"],
            date=row["date"],
            genre=row["genre"],
            disc=row["disc"],
            track=row["track"],
        )
        for row in rows
    )


def issues_of(connection: sqlite3.Connection, folder: str) -> tuple[LibraryIssue, ...]:
    """The issues recorded against one folder."""
    rows = connection.execute(
        "SELECT kind, album, detail, paths FROM issues WHERE folder = ? ORDER BY id",
        (folder,),
    )
    return tuple(
        LibraryIssue(
            kind=IssueKind(row["kind"]),
            album=row["album"],
            detail=row["detail"],
            paths=split(row["paths"]),
        )
        for row in rows
    )


def source_row(folder: str, source: SourceRecord) -> tuple[object, ...]:
    """One source as the column tuple the insert expects."""
    return (
        folder,
        source.path,
        source.file_name,
        source.start_frame,
        source.end_frame,
        source.duration_ms,
        source.sample_rate,
        source.bit_depth,
        source.album,
        source.album_artist,
        join(source.artists),
        source.title,
        source.date,
        source.genre,
        source.disc,
        source.track,
    )
