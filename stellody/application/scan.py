"""Scanning a music library, incrementally and without ever writing to it."""

from __future__ import annotations

import os
from dataclasses import dataclass, field

from stellody.application.artwork import sources_for
from stellody.application.ports import (
    CancelledCheck,
    LibraryStore,
    LibraryWalker,
    MediaProbe,
    TextReader,
)
from stellody.application.records import (
    DERIVATION,
    _grouping_entries,
    _record_from_file,
    _records_from_cue,
)
from stellody.application.scan_report import (
    ProgressCallback,
    ScanProgress,
    ScanReport,
)
from stellody.application.values import (
    AudioProperties,
    FolderListing,
    FolderRecord,
    SourceRecord,
)
from stellody.domain.cue import CueParseError, CueSheet, parse_cue
from stellody.domain.entries import stated_over
from stellody.domain.grouping import assemble_albums
from stellody.domain.health import IssueKind, LibraryIssue

SINGLE_FILE_ALBUM = 1
# What the report counts as could not be read: a file, also a whole folder
# the system would not let the walk open.
UNREADABLE = frozenset({IssueKind.UNREADABLE_FILE, IssueKind.UNREADABLE_FOLDER})
# Every character this system separates folders with, so "beneath" can be
# asked of a path written either way round.
SEPARATORS = "".join(filter(None, (os.sep, os.altsep)))


def _beyond_reach(
    cached: dict[str, FolderRecord], unlisted: list[str]
) -> list[FolderRecord]:
    """Every remembered folder at or beneath one the walk could not list.

    Beneath as well as at, since a walk that cannot open a folder cannot go
    into the folders inside it either. A neighbour that merely starts with
    the same letters, "Locked Out" beside "Locked", is not beneath it.
    """
    return [
        record
        for folder, record in cached.items()
        if any(
            folder == refused
            or (folder.startswith(refused) and folder[len(refused)] in SEPARATORS)
            for refused in unlisted
        )
    ]


class LibraryUnreachableError(RuntimeError):
    """The music folder is not there to scan, so nothing was changed.

    Raised rather than reported, because the worker already turns any failure
    into a message and leaves the library on screen exactly as it was: which
    is the right answer to a drive that is not plugged in.
    """

    def __init__(self, root: str) -> None:
        super().__init__(
            f"the music folder {root} cannot be reached; nothing in the "
            "library was changed"
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

        A root that is not there is refused before anything is touched. It
        would otherwise walk as no folders, which marks every file absent and
        empties the remembered library; an unplugged drive is not a library
        somebody deleted.
        """
        if not self._walker.reachable(root):
            raise LibraryUnreachableError(root)
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
        unlisted: list[str] = []

        for listing in self._walker.walk(root):
            if cancelled is not None and cancelled():
                return ScanReport(cancelled=True)
            if not listing.listed:
                unlisted.append(listing.folder)
                continue
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

        # What the walk could not reach is kept as it was last found, so it
        # is never marked absent: a permission the system refused is not an
        # album somebody deleted.
        for kept in _beyond_reach(cached, unlisted):
            records.append(kept)
            seen.update(kept.signatures)
        refused = tuple(
            LibraryIssue(
                kind=IssueKind.UNREADABLE_FOLDER, album=folder, paths=(folder,)
            )
            for folder in unlisted
        )
        absent = self._store.mark_absent(frozenset(seen))
        # Read after the walk rather than before it, so a correction accepted
        # while a scan was running is honoured by the library it produces.
        #
        # Assembled exactly as `LoadLibrary` assembles it, stated album values
        # first and the accepted corrections over the tracks afterwards. The
        # two readings have to agree because they are compared: the window
        # measures a scan against the library on screen, so a scan that read
        # the same unchanged music another way reported the stated album gone
        # and its raw-tagged self new, on every rescan for ever, since neither
        # reading could ever become the other. Reported from a real library on
        # 2026-09-10 as ten albums arriving and two leaving with no folder
        # re-read at all.
        entries = stated_over(_grouping_entries(records), self._store.all_album_edits())
        albums, issues = assemble_albums(entries, self._store.all_overrides())
        found = tuple(issue for record in records for issue in record.issues) + refused
        return ScanReport(
            albums=albums,
            issues=found + issues,
            art=sources_for(albums, tuple(records)),
            folders_probed=probed_folders,
            folders_reused=reused_folders,
            files_in_library=sum(len(record.stats) for record in records),
            files_unreadable=sum(1 for issue in found if issue.kind in UNREADABLE),
            files_absent=absent,
        )

    @staticmethod
    def _unchanged(
        listing: FolderListing,
        known: dict[str, tuple[int, int]],
        cached: FolderRecord,
    ) -> bool:
        """True when this folder is as it was AND was read by the current rules.

        Unchanged files are not on their own a reason to reuse a record. What
        was written down is a reading of those files, so a reading taken under
        rules that have since changed is out of date however still the folder
        has been. Left on the signatures alone, a corrected rule reaches only
        the folders somebody happens to touch, which for a settled library is
        none of them.
        """
        if cached.derivation != DERIVATION:
            return False
        # The cue sheets and pictures are compared whole, size and time
        # included, since they are not files the store tracks one by one.
        if listing.sidecar_signatures != cached.sidecar_signatures:
            return False
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
        # Files the system would not even give a size for, named as the ones
        # that would not open are, rather than left out without a word.
        state.issues.extend(
            LibraryIssue(
                kind=IssueKind.UNREADABLE_FILE, album=listing.folder, paths=(path,)
            )
            for path in listing.unreadable
        )

        self._name_the_unplayable(listing, state)
        self._collect_sources(listing, properties, state)
        return FolderRecord(
            folder=listing.folder,
            stats=tuple(item for item in listing.audio if item.path in properties),
            sources=tuple(state.sources),
            art_path=listing.image_paths[0] if listing.image_paths else "",
            has_embedded_art=state.embedded_art,
            issues=tuple(state.issues),
            derivation=DERIVATION,
            sidecars=listing.sidecars,
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
