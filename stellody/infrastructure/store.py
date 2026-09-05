"""The SQLite store: everything Stellody knows; everything it writes.

Raw tag values are persisted rather than resolved ones, so improving the
resolution rules takes effect on the next load without rescanning a library.
Files that vanish are flagged absent, never deleted.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Mapping

from stellody.application.values import FileStat, FolderRecord, SourceRecord
from stellody.domain.health import IssueKind, LibraryIssue
from stellody.domain.listening import Listening
from stellody.domain.overrides import AlbumEdit, Override
from stellody.infrastructure import album_edit_rows, override_rows

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
CREATE TABLE IF NOT EXISTS settings (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS listening (
    handle TEXT PRIMARY KEY,
    path   TEXT NOT NULL DEFAULT '',
    stars  INTEGER NOT NULL DEFAULT 0,
    plays  INTEGER NOT NULL DEFAULT 0
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


JOURNAL_MODE = "WAL"
BUSY_TIMEOUT_MS = 5000


class SqliteLibraryStore:
    """Stellody's library metadata, held in one SQLite file."""

    def __init__(self, database: str) -> None:
        self.database = database
        self._connection = sqlite3.connect(database)
        self._connection.row_factory = sqlite3.Row
        # SQLite refuses a connection used from a thread other than the one
        # that made it, so the scan opens its own against the same file. Write
        # ahead logging is what lets the two coexist: one writer and readers
        # that are not blocked by it. The busy timeout covers the moment the
        # scan commits a folder while the window stores a setting.
        # A constructor that raises leaves no object to close, so the handle
        # would be held until something collected it. On Windows that is a
        # file nobody can move: setting a damaged database aside was refused
        # by the very connection that had just failed to open it.
        try:
            self._connection.execute(f"PRAGMA journal_mode={JOURNAL_MODE}")
            self._connection.execute(f"PRAGMA busy_timeout={BUSY_TIMEOUT_MS}")
            self._connection.executescript(
                SCHEMA + override_rows.SCHEMA + album_edit_rows.SCHEMA
            )
            self._connection.commit()
        except Exception:
            self._connection.close()
            raise

    def close(self) -> None:
        """Release the database handle."""
        self._connection.close()

    def get_setting(self, key: str, default: str = "") -> str:
        """The stored value for a key; the default when it has never been set."""
        row = self._connection.execute(
            "SELECT value FROM settings WHERE key = ?", (key,)
        ).fetchone()
        return row["value"] if row is not None else default

    def set_setting(self, key: str, value: str) -> None:
        """Store a value against a key."""
        with self._connection:
            self._connection.execute(
                "INSERT INTO settings (key, value) VALUES (?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (key, value),
            )

    def all_listening(self) -> Mapping[str, Listening]:
        """Every track anybody has rated or played, by its handle.

        The whole table at once, since it holds only the tracks somebody has
        actually touched: asking per track would ask once per drawn row.
        """
        rows = self._connection.execute(
            "SELECT handle, stars, plays FROM listening"
        ).fetchall()
        return {
            row["handle"]: Listening(stars=row["stars"], plays=row["plays"])
            for row in rows
        }

    def set_listening(self, handle: str, path: str, record: Listening) -> None:
        """Write one track's rating and play count."""
        with self._connection:
            self._connection.execute(
                "INSERT INTO listening (handle, path, stars, plays) "
                "VALUES (?, ?, ?, ?) ON CONFLICT(handle) DO UPDATE SET "
                "path = excluded.path, stars = excluded.stars, "
                "plays = excluded.plays",
                (handle, path, record.stars, record.plays),
            )

    def all_overrides(self) -> tuple[Override, ...]:
        """Every correction a listener has accepted."""
        return override_rows.all_overrides(self._connection)

    def accept_overrides(self, accepted: tuple[Override, ...]) -> None:
        """Record corrections as accepted, replacing any already standing."""
        override_rows.accept(self._connection, accepted)

    def discard_overrides(self, unwanted: tuple[Override, ...]) -> None:
        """Take corrections back, so the automatic rules show through again."""
        override_rows.discard(self._connection, unwanted)

    def all_album_edits(self) -> tuple[AlbumEdit, ...]:
        """Everything a listener has stated about an album itself."""
        return album_edit_rows.all_album_edits(self._connection)

    def state_album_edits(self, stated: tuple[AlbumEdit, ...]) -> None:
        """Record what has been stated, replacing anything standing."""
        album_edit_rows.state(self._connection, stated)

    def discard_album_edits(self, unwanted: tuple[AlbumEdit, ...]) -> None:
        """Withdraw statements, so the tags name the album again."""
        album_edit_rows.discard(self._connection, unwanted)

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
