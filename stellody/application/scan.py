"""Scanning a music library, incrementally and without ever writing to it."""

from __future__ import annotations

import os
from collections.abc import Callable
from dataclasses import dataclass, field

from stellody.application.artwork import AlbumArtSources, sources_for
from stellody.application.ports import (
    CancelledCheck,
    LibraryStore,
    LibraryWalker,
    MediaProbe,
    TextReader,
)
from stellody.application.records import (
    _grouping_entries,
    _record_from_file,
    _records_from_cue,
)
from stellody.application.values import (
    AudioProperties,
    FolderListing,
    FolderRecord,
    SourceRecord,
)
from stellody.domain.album import Album
from stellody.domain.cue import CueParseError, CueSheet, parse_cue
from stellody.domain.entries import stated_over
from stellody.domain.grouping import assemble_albums
from stellody.domain.health import IssueKind, LibraryIssue

SINGLE_FILE_ALBUM = 1
PERCENT = 100


@dataclass(frozen=True, slots=True)
class ScanProgress:
    """How far through a scan is, plus which folder it is reading.

    A library of a few thousand folders spends long enough scanning that a bar
    with no number on it says only that something is happening. The count is
    carried here rather than worked out on the interface thread, which has no
    way of knowing how many folders there are.
    """

    folder: str
    done: int = 0
    total: int = 0

    @property
    def percent(self) -> int:
        """How far through, as a whole number; nought when nothing is known."""
        if self.total <= 0:
            return 0
        return round(self.done * PERCENT / self.total)


ProgressCallback = Callable[[ScanProgress], None]
# Asked between folders, so a scan can be given up without waiting for it. A
# scan of a large library takes long enough that quitting during one is an
# ordinary thing to do; Qt cannot interrupt a running one from outside.


@dataclass(frozen=True, slots=True)
class LibraryView:
    """A library as it stands, with nothing said about how it got here.

    A scan reports counts of what it read; a load has read nothing, so it
    reports none, rather than zeroes that would read as a scan finding
    nothing.
    """

    albums: tuple[Album, ...] = ()
    issues: tuple[LibraryIssue, ...] = ()
    art: tuple[AlbumArtSources, ...] = ()

    @property
    def track_count(self) -> int:
        """How many tracks the assembled library holds."""
        return sum(album.track_count for album in self.albums)


@dataclass(frozen=True, slots=True)
class ScanReport:
    """What one scan found, plus how much of it had to be re-read."""

    albums: tuple[Album, ...] = ()
    issues: tuple[LibraryIssue, ...] = ()
    art: tuple[AlbumArtSources, ...] = ()
    folders_probed: int = 0
    folders_reused: int = 0
    # Every readable audio file the library holds, NOT the files this scan
    # opened. A reused folder contributes its remembered files without one of
    # them being touched, so on a rescan that changed nothing this is the whole
    # library while nothing at all was read. It was called files_probed, which
    # said the opposite and was reported to a listener as "Files read".
    files_in_library: int = 0
    files_unreadable: int = 0
    files_absent: int = 0
    cancelled: bool = False

    @property
    def track_count(self) -> int:
        """How many tracks the assembled library holds."""
        return sum(album.track_count for album in self.albums)

    @property
    def folders_checked(self) -> int:
        """Every folder the walk visited, whether or not it had to be re-read.

        A rescan that finds nothing changed still lists every folder and
        compares every file's size and modification time against the store.
        Reporting only the folders it re-read says nought, which reads as a
        scan that did nothing rather than as one that found nothing to do.
        """
        return self.folders_probed + self.folders_reused


class LoadLibrary:
    """Assembles the library the store already holds, reading no music at all.

    Starting the application is not a request to scan. On a library of any
    size a walk is felt; it reaches for a drive that may be asleep, absent or
    somebody else's machine over a network. What the store holds is
    what the last scan found, which is what the user last saw; anything newer
    arrives when they ask for it by rescanning.
    """

    def __init__(self, store: LibraryStore) -> None:
        self._store = store

    def run(self) -> LibraryView:
        """The remembered library, assembled from stored records."""
        records = tuple(self._store.load_folders())
        # Stated album values first, since they decide what an album IS and so
        # what folds with what; the accepted corrections are laid over the
        # tracks afterwards, which is where they have always gone.
        entries = stated_over(_grouping_entries(records), self._store.all_album_edits())
        albums, issues = assemble_albums(entries, self._store.all_overrides())
        return LibraryView(
            albums=albums,
            issues=tuple(issue for record in records for issue in record.issues)
            + issues,
            art=sources_for(albums, records),
        )


@dataclass(slots=True)
class _Probed:
    """Accumulated results while one folder is being read."""

    sources: list[SourceRecord] = field(default_factory=list)
    issues: list[LibraryIssue] = field(default_factory=list)
    probed: int = 0
    unreadable: int = 0
    embedded_art: bool = False


class ScanLibrary:
    """Reads a library folder into Stellody's own store.

    Folders whose files are unchanged since the last scan are reused from the
    store rather than reprobed, so adding one album re-reads one folder.
    """

    def __init__(
        self,
        walker: LibraryWalker,
        probe: MediaProbe,
        cue_reader: TextReader,
        store: LibraryStore,
    ) -> None:
        self._walker = walker
        self._probe = probe
        self._cue_reader = cue_reader
        self._store = store

    def run(
        self,
        root: str,
        progress: ProgressCallback | None = None,
        cancelled: CancelledCheck | None = None,
    ) -> ScanReport:
        """Scan a root folder and return the assembled library.

        A cancelled scan reports nothing found rather than a short library.
        Every folder read before it stopped is already saved, so the work is
        kept; what is NOT done is deciding which files have gone, since a scan
        that stopped early has no idea what it did not reach.
        """
        known = dict(self._store.file_signatures())
        cached = {record.folder: record for record in self._store.load_folders()}
        seen: set[str] = set()
        records: list[FolderRecord] = []
        probed_folders = 0
        reused_folders = 0
        # Counted before the walk, because the walk knows the total only once
        # it has finished, by which time the number is of no use to anybody.
        total = self._walker.count(root)
        done = 0

        for listing in self._walker.walk(root):
            if cancelled is not None and cancelled():
                return ScanReport(cancelled=True)
            done += 1
            if progress is not None:
                progress(ScanProgress(listing.folder, done, total))
            seen.update(item.path for item in listing.audio)
            reusable = cached.get(listing.folder)
            if reusable is not None and self._unchanged(listing, known, reusable):
                records.append(reusable)
                reused_folders += 1
                continue
            record = self._probe_folder(listing)
            self._store.save_folder(record)
            records.append(record)
            probed_folders += 1

        absent = self._store.mark_absent(frozenset(seen))
        # Read after the walk rather than before it, so a correction accepted
        # while a scan was running is honoured by the library it produces.
        albums, issues = assemble_albums(
            _grouping_entries(records), self._store.all_overrides()
        )
        return ScanReport(
            albums=albums,
            issues=tuple(issue for record in records for issue in record.issues)
            + issues,
            art=sources_for(albums, tuple(records)),
            folders_probed=probed_folders,
            folders_reused=reused_folders,
            files_in_library=sum(len(record.stats) for record in records),
            files_unreadable=sum(
                1
                for record in records
                for issue in record.issues
                if issue.kind is IssueKind.UNREADABLE_FILE
            ),
            files_absent=absent,
        )

    @staticmethod
    def _unchanged(
        listing: FolderListing,
        known: dict[str, tuple[int, int]],
        cached: FolderRecord,
    ) -> bool:
        """True when a folder's files are exactly as they were last scan."""
        current = listing.signatures
        if set(current) != set(cached.signatures):
            return False
        return all(known.get(path) == signature for path, signature in current.items())

    def _probe_folder(self, listing: FolderListing) -> FolderRecord:
        """Read every audio file in one folder, cue sheet included."""
        state = _Probed()
        properties: dict[str, AudioProperties] = {}
        for item in listing.audio:
            read = self._probe.read(item.path)
            if read is None or read.sample_rate <= 0:
                state.unreadable += 1
                state.issues.append(
                    LibraryIssue(
                        kind=IssueKind.UNREADABLE_FILE,
                        album=listing.folder,
                        paths=(item.path,),
                    )
                )
                continue
            state.probed += 1
            properties[item.path] = read
            state.embedded_art = state.embedded_art or read.has_embedded_art

        self._name_the_unplayable(listing, state)
        self._collect_sources(listing, properties, state)
        return FolderRecord(
            folder=listing.folder,
            stats=tuple(item for item in listing.audio if item.path in properties),
            sources=tuple(state.sources),
            art_path=listing.image_paths[0] if listing.image_paths else "",
            has_embedded_art=state.embedded_art,
            issues=tuple(state.issues),
        )

    @staticmethod
    def _name_the_unplayable(listing: FolderListing, state: _Probed) -> None:
        """Say what this folder holds that this build cannot decode.

        ONE finding for the folder rather than one a file. A library can hold a
        thousand such tracks; a thousand entries is not a report anybody reads.
        What a listener needs is which albums are missing and why. Nothing is
        opened to say it, since the suffix is the whole of what is known here
        and opening them is precisely what cannot be done.
        """
        if not listing.unplayable:
            return
        kinds = sorted(
            {os.path.splitext(path)[1].casefold() for path in listing.unplayable}
        )
        state.issues.append(
            LibraryIssue(
                kind=IssueKind.UNPLAYABLE_FORMAT,
                album=listing.folder,
                detail=f"{len(listing.unplayable)} file(s), {' '.join(kinds)}",
                paths=tuple(listing.unplayable),
            )
        )

    def _collect_sources(
        self,
        listing: FolderListing,
        properties: dict[str, AudioProperties],
        state: _Probed,
    ) -> None:
        """Turn a folder's probed files into sources, honouring a cue sheet."""
        readable = [item for item in listing.audio if item.path in properties]
        if len(readable) == SINGLE_FILE_ALBUM and listing.cue_paths:
            only = readable[0]
            sheet = self._read_cue(listing.cue_paths[0], properties[only.path])
            if sheet is not None and sheet.tracks:
                state.sources.extend(
                    _records_from_cue(
                        only.path, only.file_name, properties[only.path], sheet
                    )
                )
                return
        for item in readable:
            state.sources.append(
                _record_from_file(item.path, item.file_name, properties[item.path])
            )

    def _read_cue(self, path: str, properties: AudioProperties) -> CueSheet | None:
        """Parse the cue sheet beside a single-file album, when it is usable."""
        text = self._cue_reader.read(path)
        if text is None:
            return None
        try:
            return parse_cue(text, properties.sample_rate)
        except CueParseError:
            return None
