"""The SQLite store: everything Stellody knows; everything it writes.

Raw tag values are persisted rather than resolved ones, so improving the
resolution rules takes effect on the next load without rescanning a library.
Files that vanish are flagged absent, never deleted.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Mapping

from stellody.application.ports import FileStat, FolderRecord, SourceRecord
from stellody.domain.health import IssueKind, LibraryIssue

UNIT_SEPARATOR = "\x1f"

SCHEMA = """
CREATE TABLE IF NOT EXISTS folders (
    folder            TEXT PRIMARY KEY,
    art_path          TEXT NOT NULL DEFAULT '',
    has_embedded_art  INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS files (
    path      TEXT PRIMARY KEY,
    folder    TEXT NOT NULL,
    file_name TEXT NOT NULL,
    size      INTEGER NOT NULL,
    mtime     INTEGER NOT NULL,
    present   INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE IF NOT EXISTS sources (
    id           INTEGER PRIMARY KEY,
    folder       TEXT NOT NULL,
    path         TEXT NOT NULL,
    file_name    TEXT NOT NULL,
    start_frame  INTEGER NOT NULL DEFAULT 0,
    end_frame    INTEGER,
    duration_ms  INTEGER NOT NULL DEFAULT 0,
    sample_rate  INTEGER NOT NULL DEFAULT 0,
    bit_depth    INTEGER NOT NULL DEFAULT 0,
    album        TEXT NOT NULL DEFAULT '',
    album_artist TEXT NOT NULL DEFAULT '',
    artists      TEXT NOT NULL DEFAULT '',
    title        TEXT NOT NULL DEFAULT '',
    date         TEXT NOT NULL DEFAULT '',
    genre        TEXT NOT NULL DEFAULT '',
    disc         INTEGER,
    track        INTEGER
);
CREATE TABLE IF NOT EXISTS issues (
    id     INTEGER PRIMARY KEY,
    folder TEXT NOT NULL,
    kind   TEXT NOT NULL,
    album  TEXT NOT NULL,
    detail TEXT NOT NULL DEFAULT '',
    paths  TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS files_by_folder ON files (folder);
CREATE INDEX IF NOT EXISTS sources_by_folder ON sources (folder);
CREATE INDEX IF NOT EXISTS issues_by_folder ON issues (folder);
"""

_SOURCE_COLUMNS = (
    "path, file_name, start_frame, end_frame, duration_ms, sample_rate, "
    "bit_depth, album, album_artist, artists, title, date, genre, disc, track"
)


def _join(values: tuple[str, ...]) -> str:
    """Pack a tuple of strings into one column."""
    return UNIT_SEPARATOR.join(values)


def _split(value: str) -> tuple[str, ...]:
    """Unpack a column written by _join."""
    return tuple(part for part in value.split(UNIT_SEPARATOR) if part)


class SqliteLibraryStore:
    """Stellody's library metadata, held in one SQLite file."""

    def __init__(self, database: str) -> None:
        self._connection = sqlite3.connect(database)
        self._connection.row_factory = sqlite3.Row
        self._connection.executescript(SCHEMA)
        self._connection.commit()

    def close(self) -> None:
        """Release the database handle."""
        self._connection.close()

    def file_signatures(self) -> Mapping[str, tuple[int, int]]:
        """Every present file against its recorded size and mtime."""
        rows = self._connection.execute(
            "SELECT path, size, mtime FROM files WHERE present = 1"
        )
        return {row["path"]: (row["size"], row["mtime"]) for row in rows}

    def load_folders(self) -> tuple[FolderRecord, ...]:
        """Every folder record currently held."""
        folders = self._connection.execute(
            "SELECT folder, art_path, has_embedded_art FROM folders ORDER BY folder"
        ).fetchall()
        return tuple(
            FolderRecord(
                folder=row["folder"],
                stats=self._stats_of(row["folder"]),
                sources=self._sources_of(row["folder"]),
                art_path=row["art_path"],
                has_embedded_art=bool(row["has_embedded_art"]),
                issues=self._issues_of(row["folder"]),
            )
            for row in folders
        )

    def save_folder(self, record: FolderRecord) -> None:
        """Replace one folder's record with a freshly scanned one."""
        with self._connection:
            self._clear_folder(record.folder)
            self._connection.execute(
                "INSERT INTO folders (folder, art_path, has_embedded_art) "
                "VALUES (?, ?, ?)",
                (record.folder, record.art_path, int(record.has_embedded_art)),
            )
            self._connection.executemany(
                "INSERT INTO files (path, folder, file_name, size, mtime, present) "
                "VALUES (?, ?, ?, ?, ?, 1)",
                [
                    (item.path, record.folder, item.file_name, item.size, item.mtime)
                    for item in record.stats
                ],
            )
            self._connection.executemany(
                f"INSERT INTO sources (folder, {_SOURCE_COLUMNS}) VALUES "
                "(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                [_source_row(record.folder, source) for source in record.sources],
            )
            self._connection.executemany(
                "INSERT INTO issues (folder, kind, album, detail, paths) "
                "VALUES (?, ?, ?, ?, ?)",
                [
                    (
                        record.folder,
                        str(issue.kind),
                        issue.album,
                        issue.detail,
                        _join(issue.paths),
                    )
                    for issue in record.issues
                ],
            )

    def mark_absent(self, seen_paths: frozenset[str]) -> int:
        """Flag files no longer on disk. Their metadata is kept."""
        with self._connection:
            self._connection.execute(
                "CREATE TEMPORARY TABLE IF NOT EXISTS seen (path TEXT PRIMARY KEY)"
            )
            self._connection.execute("DELETE FROM seen")
            self._connection.executemany(
                "INSERT OR IGNORE INTO seen (path) VALUES (?)",
                [(path,) for path in seen_paths],
            )
            cursor = self._connection.execute(
                "UPDATE files SET present = 0 WHERE present = 1 "
                "AND path NOT IN (SELECT path FROM seen)"
            )
            missing = cursor.rowcount
            self._connection.execute(
                "UPDATE files SET present = 1 WHERE present = 0 "
                "AND path IN (SELECT path FROM seen)"
            )
        return max(missing, 0)

    def _clear_folder(self, folder: str) -> None:
        """Remove every row belonging to one folder."""
        for table in ("issues", "sources", "files", "folders"):
            self._connection.execute(f"DELETE FROM {table} WHERE folder = ?", (folder,))

    def _stats_of(self, folder: str) -> tuple[FileStat, ...]:
        """The recorded file statistics for one folder."""
        rows = self._connection.execute(
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

    def _sources_of(self, folder: str) -> tuple[SourceRecord, ...]:
        """The stored sources for one folder, tags exactly as they were read."""
        rows = self._connection.execute(
            f"SELECT {_SOURCE_COLUMNS} FROM sources "
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
                artists=_split(row["artists"]),
                title=row["title"],
                date=row["date"],
                genre=row["genre"],
                disc=row["disc"],
                track=row["track"],
            )
            for row in rows
        )

    def _issues_of(self, folder: str) -> tuple[LibraryIssue, ...]:
        """The issues recorded against one folder."""
        rows = self._connection.execute(
            "SELECT kind, album, detail, paths FROM issues "
            "WHERE folder = ? ORDER BY id",
            (folder,),
        )
        return tuple(
            LibraryIssue(
                kind=IssueKind(row["kind"]),
                album=row["album"],
                detail=row["detail"],
                paths=_split(row["paths"]),
            )
            for row in rows
        )


def _source_row(folder: str, source: SourceRecord) -> tuple[object, ...]:
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
        _join(source.artists),
        source.title,
        source.date,
        source.genre,
        source.disc,
        source.track,
    )
