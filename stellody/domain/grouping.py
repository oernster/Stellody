"""Assembling scanned sources into albums.

**Folders group, tags name.** A folder is one album, with sibling CD1 and CD2
folders merged into one multi-disc set. The tags then supply that album's
title, artist, date and genre.

Grouping by tags was tried first and measured against a real library: classical
rips frequently carry the composer in the ALBUM tag and a different DATE on
every track, which fragmented one folder into five albums. A folder boundary is
what a ripper actually records, so that is what is trusted.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from stellody.domain.album import Album
from stellody.domain.health import IssueKind, LibraryIssue
from stellody.domain.identity import AlbumIdentity
from stellody.domain.ordering import TrackCandidate, resolve_tracks
from stellody.domain.text import VARIOUS_ARTISTS, comparison_key, normalise

UNKNOWN_ALBUM = "Unknown Album"

# "The Book of Souls CD1", "White Album (Disc 2)", "Box Set [Disk 3]".
# The literal CD or Disc word is required, so an album whose title merely ends
# in a number, such as Northern Exposure 2, is never split.
_DISC_SUFFIX = re.compile(
    r"^(?P<base>.*?)[\s._-]*[(\[]?\s*(?:CD|Disc|Disk)\s*[.\-_]?\s*"
    r"(?P<number>\d{1,2})\s*[)\]]?$",
    re.IGNORECASE,
)


@dataclass(frozen=True, slots=True)
class SourceEntry:
    """One scanned source, with the folder context needed to place it."""

    folder_name: str
    parent_path: str
    parent_name: str
    candidate: TrackCandidate
    album: str = ""
    album_artist: str = ""
    date: str = ""
    genre: str = ""


def folder_base_and_disc(folder_name: str) -> tuple[str, int | None]:
    """Split a trailing disc marker off a folder name.

    Returns the name without the marker and the disc number it carried; the
    name unchanged and None when it carried none.
    """
    match = _DISC_SUFFIX.match(folder_name)
    if match is None:
        return folder_name, None
    base = match.group("base").strip()
    if not base:
        return folder_name, None
    return base, int(match.group("number"))


def _most_common(values: list[str]) -> str:
    """The most frequent non-empty value, ties broken alphabetically."""
    counts: dict[str, int] = {}
    for value in values:
        if value:
            counts[value] = counts.get(value, 0) + 1
    if not counts:
        return ""
    return max(counts, key=lambda name: (counts[name], name))


@dataclass(slots=True)
class _Group:
    """One album's worth of entries, accumulated by folder."""

    base_name: str
    parent_name: str
    candidates: list[TrackCandidate]
    albums: list[str]
    artists: list[str]
    dates: list[str]
    genres: list[str]
    tagged_artists: int
    disc_conflicts: list[str]


def _apply_folder_disc(
    candidate: TrackCandidate, folder_disc: int | None
) -> TrackCandidate:
    """Set a candidate's disc from its folder name, which outranks the tag.

    A folder named "(Disc 2)" is a statement by whoever laid the rip out. A
    DISCNUMBER tag contradicting it was written by software; in the
    reference library one such folder holds tags claiming discs 1, 2 and 3.
    """
    if folder_disc is None or candidate.tag_disc == folder_disc:
        return candidate
    return TrackCandidate(
        file_name=candidate.file_name,
        source=candidate.source,
        duration_ms=candidate.duration_ms,
        sample_rate=candidate.sample_rate,
        bit_depth=candidate.bit_depth,
        tag_disc=folder_disc,
        tag_track=candidate.tag_track,
        tag_title=candidate.tag_title,
        artists=candidate.artists,
    )


def _identity_of(group: _Group) -> AlbumIdentity:
    """Name an album from the tags its tracks carry, falling back to folders."""
    title = _most_common(group.albums) or normalise(group.base_name) or UNKNOWN_ALBUM
    artist = _most_common(group.artists)
    if not artist:
        artist = normalise(group.parent_name) or VARIOUS_ARTISTS
    return AlbumIdentity(
        album_artist=artist,
        title=title,
        date=_most_common(group.dates),
    )


def _collect(entries: tuple[SourceEntry, ...]) -> dict[tuple[str, str], _Group]:
    """Bucket entries into one group per album folder."""
    groups: dict[tuple[str, str], _Group] = {}
    for entry in entries:
        base, folder_disc = folder_base_and_disc(entry.folder_name)
        key = (entry.parent_path, comparison_key(base))
        group = groups.get(key)
        if group is None:
            group = _Group(
                base_name=base,
                parent_name=entry.parent_name,
                candidates=[],
                albums=[],
                artists=[],
                dates=[],
                genres=[],
                tagged_artists=0,
                disc_conflicts=[],
            )
            groups[key] = group
        if (
            folder_disc is not None
            and entry.candidate.tag_disc is not None
            and entry.candidate.tag_disc != folder_disc
        ):
            group.disc_conflicts.append(entry.candidate.file_name)
        group.candidates.append(_apply_folder_disc(entry.candidate, folder_disc))
        group.albums.append(normalise(entry.album))
        artist = normalise(entry.album_artist)
        group.artists.append(artist)
        if artist:
            group.tagged_artists += 1
        group.dates.append(normalise(entry.date))
        group.genres.append(normalise(entry.genre))
    return groups


def assemble_albums(
    entries: tuple[SourceEntry, ...],
) -> tuple[tuple[Album, ...], tuple[LibraryIssue, ...]]:
    """Group scanned sources into ordered albums, reporting what was inferred."""
    groups = _collect(entries)
    built: list[tuple[AlbumIdentity, Album]] = []
    issues: list[LibraryIssue] = []

    for group in groups.values():
        identity = _identity_of(group)
        label = f"{identity.display_artist} - {identity.display_title}"
        tracks, track_issues = resolve_tracks(tuple(group.candidates), label)
        issues.extend(track_issues)
        if group.disc_conflicts:
            issues.append(
                LibraryIssue(
                    kind=IssueKind.DISC_NUMBER_CONFLICT,
                    album=label,
                    detail=f"{len(group.disc_conflicts)} file(s)",
                    paths=tuple(group.disc_conflicts),
                )
            )
        if not group.tagged_artists:
            issues.append(
                LibraryIssue(
                    kind=IssueKind.MISSING_ALBUM_ARTIST,
                    album=label,
                    detail=f"{len(group.candidates)} file(s)",
                )
            )
        built.append(
            (
                identity,
                Album(
                    identity=identity,
                    tracks=tracks,
                    genre=_most_common(group.genres),
                ),
            )
        )

    built.sort(key=lambda pair: pair[0].sort_key)
    return tuple(album for _, album in built), tuple(issues)
