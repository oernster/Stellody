"""Turning what was read off disk into records, then records into entries.

The pieces a scan and a load both need: how long a file plays, what one file
or one cue sheet contributes as stored records, plus how a stored record
reads as an entry for grouping. None of it knows where the folders came from, which
is why it sits apart from the scanning itself.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from stellody.application import tags
from stellody.application.values import AudioProperties, FolderRecord, SourceRecord
from stellody.domain.cue import CueSheet
from stellody.domain.grouping import SourceEntry
from stellody.domain.text import tag_date
from stellody.domain.track import MILLISECONDS_PER_SECOND


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
        date=tag_date(tags.first(properties.tags, tags.DATE)),
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
                date=tag_date(sheet.date or fallback.date),
                genre=sheet.genre or fallback.genre,
                # A set spanning folders states which disc each one is, so
                # taking it is what keeps two discs from claiming one another's
                # track numbers. Without it a bonus disc whose folder is not
                # named CD2 collided with disc one on every track it held.
                disc=sheet.disc if sheet.disc is not None else fallback.disc,
                track=cue_track.number,
            )
        )
    return tuple(records)


def _grouping_entries(records: Sequence[FolderRecord]) -> tuple[SourceEntry, ...]:
    """Every stored source as a grouping entry, with its folder context.

    Shared by the two ways a library is assembled: from a scan that has just
    read the folders; from the store alone.
    """
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
