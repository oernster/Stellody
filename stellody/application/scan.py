"""Scanning a music library, incrementally and without ever writing to it."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from stellody.application import tags
from stellody.application.ports import (
    AudioProperties,
    FolderListing,
    FolderRecord,
    LibraryStore,
    LibraryWalker,
    MediaProbe,
    SourceRecord,
    TextReader,
)
from stellody.domain.album import Album
from stellody.domain.cue import CueParseError, CueSheet, parse_cue
from stellody.domain.grouping import SourceEntry, assemble_albums
from stellody.domain.health import IssueKind, LibraryIssue
from stellody.domain.track import MILLISECONDS_PER_SECOND

SINGLE_FILE_ALBUM = 1

ProgressCallback = Callable[[str], None]


@dataclass(frozen=True, slots=True)
class ScanReport:
    """What one scan found, plus how much of it had to be re-read."""

    albums: tuple[Album, ...] = ()
    issues: tuple[LibraryIssue, ...] = ()
    folders_probed: int = 0
    folders_reused: int = 0
    files_probed: int = 0
    files_unreadable: int = 0
    files_absent: int = 0

    @property
    def track_count(self) -> int:
        """How many tracks the assembled library holds."""
        return sum(album.track_count for album in self.albums)


@dataclass(frozen=True, slots=True)
class _FolderContext:
    """The names a folder contributes when its tags fall short."""

    folder_name: str
    parent_path: str
    parent_name: str


def _duration_ms(frames: int, sample_rate: int) -> int:
    """Milliseconds for a frame count at a sample rate.

    The caller guarantees a positive rate: a file whose header claims none is
    reported as unreadable rather than reaching here.
    """
    return frames * MILLISECONDS_PER_SECOND // sample_rate


def _record_from_file(
    path: str, file_name: str, properties: AudioProperties
) -> SourceRecord:
    """One whole file as a single source."""
    return SourceRecord(
        path=path,
        file_name=file_name,
        duration_ms=_duration_ms(properties.frame_count, properties.sample_rate),
        sample_rate=properties.sample_rate,
        bit_depth=properties.bit_depth,
        album=tags.first(properties.tags, tags.ALBUM),
        album_artist=tags.first(properties.tags, tags.ALBUM_ARTIST),
        artists=tags.artists(properties.tags),
        title=tags.first(properties.tags, tags.TITLE),
        date=tags.first(properties.tags, tags.DATE),
        genre=tags.first(properties.tags, tags.GENRE),
        disc=tags.number(properties.tags, tags.DISC),
        track=tags.number(properties.tags, tags.TRACK),
    )


def _records_from_cue(
    path: str,
    file_name: str,
    properties: AudioProperties,
    sheet: CueSheet,
) -> tuple[SourceRecord, ...]:
    """A cue sheet's tracks as slices of one file."""
    fallback = _record_from_file(path, file_name, properties)
    records: list[SourceRecord] = []
    for cue_track in sheet.tracks:
        end = cue_track.end_frame
        if end is None and properties.frame_count > cue_track.start_frame:
            end = properties.frame_count
        length = (end - cue_track.start_frame) if end is not None else 0
        records.append(
            SourceRecord(
                path=path,
                file_name=f"{cue_track.number:02d}. {cue_track.title}",
                start_frame=cue_track.start_frame,
                end_frame=end,
                duration_ms=_duration_ms(length, properties.sample_rate),
                sample_rate=properties.sample_rate,
                bit_depth=properties.bit_depth,
                album=sheet.album_title or fallback.album,
                album_artist=sheet.album_performer or fallback.album_artist,
                artists=cue_track.performers or fallback.artists,
                title=cue_track.title,
                date=sheet.date or fallback.date,
                genre=sheet.genre or fallback.genre,
                track=cue_track.number,
            )
        )
    return tuple(records)


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

    def run(self, root: str, progress: ProgressCallback | None = None) -> ScanReport:
        """Scan a root folder and return the assembled library."""
        known = dict(self._store.file_signatures())
        cached = {record.folder: record for record in self._store.load_folders()}
        seen: set[str] = set()
        records: list[FolderRecord] = []
        probed_folders = 0
        reused_folders = 0

        for listing in self._walker.walk(root):
            if progress is not None:
                progress(listing.folder)
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
        albums, issues = assemble_albums(self._entries(records))
        return ScanReport(
            albums=albums,
            issues=tuple(issue for record in records for issue in record.issues)
            + issues,
            folders_probed=probed_folders,
            folders_reused=reused_folders,
            files_probed=sum(len(record.stats) for record in records),
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

    @staticmethod
    def _entries(records: tuple[FolderRecord, ...] | list[FolderRecord]):
        """Every stored source as a grouping entry, with its folder context."""
        entries: list[SourceEntry] = []
        for record in records:
            context = _split_folder(record.folder)
            for source in record.sources:
                entries.append(
                    SourceEntry(
                        folder_name=context.folder_name,
                        parent_path=context.parent_path,
                        parent_name=context.parent_name,
                        candidate=source.candidate,
                        album=source.album,
                        album_artist=source.album_artist,
                        date=source.date,
                        genre=source.genre,
                    )
                )
        return tuple(entries)

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

        self._collect_sources(listing, properties, state)
        return FolderRecord(
            folder=listing.folder,
            stats=tuple(item for item in listing.audio if item.path in properties),
            sources=tuple(state.sources),
            art_path=listing.image_paths[0] if listing.image_paths else "",
            has_embedded_art=state.embedded_art,
            issues=tuple(state.issues),
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


def _split_folder(folder: str) -> _FolderContext:
    """Split a folder path into its own name and its parent's name.

    Path work rather than filesystem work: no directory is opened, so this
    stays inside the application layer.
    """
    parts = [part for part in folder.replace("\\", "/").split("/") if part]
    name = parts[-1] if parts else folder
    parent = parts[-2] if len(parts) > 1 else ""
    return _FolderContext(
        folder_name=name,
        parent_path="/".join(parts[:-1]),
        parent_name=parent,
    )
