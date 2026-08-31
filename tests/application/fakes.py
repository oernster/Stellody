"""Hand-written stand-ins for the ports, in place of a mocking library."""

from __future__ import annotations

from collections.abc import Iterator, Mapping

from stellody.application.values import (
    AudioProperties,
    FileStat,
    FolderListing,
    FolderRecord,
)

CD_RATE = 44100
CD_DEPTH = 16


def stat(path: str, name: str, size: int = 100, mtime: int = 10) -> FileStat:
    """A file statistic with defaults that rarely matter to a test."""
    return FileStat(path=path, file_name=name, size=size, mtime=mtime)


def properties(
    frames: int = CD_RATE,
    rate: int = CD_RATE,
    art: bool = False,
    **tags: tuple[str, ...],
) -> AudioProperties:
    """Probe output, with tag names given as keyword arguments."""
    return AudioProperties(
        sample_rate=rate,
        bit_depth=CD_DEPTH,
        frame_count=frames,
        has_embedded_art=art,
        tags=dict(tags),
    )


class FakeWalker:
    """Yields a fixed set of listings."""

    def __init__(self, listings: tuple[FolderListing, ...]) -> None:
        self.listings = listings
        self.roots: list[str] = []
        self.counted: list[str] = []

    def walk(self, root: str) -> Iterator[FolderListing]:
        """Record the root asked for, then replay the fixed listings."""
        self.roots.append(root)
        yield from self.listings

    def count(self, root: str) -> int:
        """Record the root asked about, then say how many are coming."""
        self.counted.append(root)
        return len(self.listings)


class FakeProbe:
    """Returns prepared properties; None for a path it does not know."""

    def __init__(self, results: Mapping[str, AudioProperties | None]) -> None:
        self.results = dict(results)
        self.reads: list[str] = []

    def read(self, path: str) -> AudioProperties | None:
        """Replay the prepared result for this path."""
        self.reads.append(path)
        return self.results.get(path)


class FakeTextReader:
    """Returns prepared text; None for a path it does not know."""

    def __init__(self, texts: Mapping[str, str | None] | None = None) -> None:
        self.texts = dict(texts or {})

    def read(self, path: str) -> str | None:
        """Replay the prepared text for this path."""
        return self.texts.get(path)


class FakeStore:
    """An in-memory library store that records what was asked of it."""

    def __init__(self, records: tuple[FolderRecord, ...] = ()) -> None:
        self.records = {record.folder: record for record in records}
        self.saved: list[str] = []
        self.absent_calls: list[frozenset[str]] = []
        self.absent_result = 0

    def file_signatures(self) -> Mapping[str, tuple[int, int]]:
        """Every recorded file against its size and mtime."""
        return {
            item.path: item.signature
            for record in self.records.values()
            for item in record.stats
        }

    def load_folders(self) -> tuple[FolderRecord, ...]:
        """Every folder record held."""
        return tuple(self.records.values())

    def save_folder(self, record: FolderRecord) -> None:
        """Replace one folder's record."""
        self.records[record.folder] = record
        self.saved.append(record.folder)

    def mark_absent(self, seen_paths: frozenset[str]) -> int:
        """Record the call and report the prepared count."""
        self.absent_calls.append(seen_paths)
        return self.absent_result
