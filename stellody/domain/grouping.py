"""Assembling scanned sources into albums.

**Folders group, tags name.** A folder is one album, with sibling CD1 and CD2
folders merged into one multi-disc set. The tags then supply that album's
title, artist, date and genre.

A bonus disc is a disc even where its folder names no number. "Ether Song
(Bonus Disc)" beside "Ether Song" is one album in two folders, so it is folded
in like a numbered one. Which disc it is then has to come from somewhere else:
the tags where they say, else the disc after whatever the album already holds,
since a bonus disc is never the first one.

Grouping by tags was tried first and measured against a real library: classical
rips frequently carry the composer in the ALBUM tag and a different DATE on
every track, which fragmented one folder into five albums. A folder boundary is
what a ripper actually records, so that is what is trusted.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from stellody.domain import overrides
from stellody.domain.album import FIRST_DISC, Album
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

# "Ether Song (Bonus Disc)", "Album [Extra CD]", "Album - Bonus Disc 2". The
# number is optional here BECAUSE the bonus word is required: that word is what
# says the folder holds another disc of the album beside it, so nothing is
# inferred from a name merely ending in the word Disc. Tried before the pattern
# above, since a numbered bonus folder matches both and only this one reads it
# without leaving half the bracket in the album name.
_BONUS_SUFFIX = re.compile(
    r"^(?P<base>.*?)[\s._-]*[(\[]?\s*(?:bonus|extra)\s*"
    r"(?:CD|Disc|Disk)\s*[.\-_]?\s*(?P<number>\d{1,2})?\s*[)\]]?$",
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
    name unchanged and None when it carried none. A bonus disc is a marker even
    where it names no number, so it folds into the album beside it and leaves
    which disc it is to be worked out.
    """
    for pattern in (_BONUS_SUFFIX, _DISC_SUFFIX):
        match = pattern.match(folder_name)
        if match is None:
            continue
        base = match.group("base").strip()
        if not base:
            continue
        number = match.group("number")
        return base, int(number) if number else None
    return folder_name, None


def is_unnumbered_bonus(folder_name: str) -> bool:
    """Whether this folder calls itself a bonus disc without saying which."""
    match = _BONUS_SUFFIX.match(folder_name)
    return (
        match is not None
        and bool(match.group("base").strip())
        and match.group("number") is None
    )


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
    # Where in `candidates` a folder calling itself a bonus disc landed without
    # saying which disc it is.
    bonus_positions: list[int]


def _with_disc(candidate: TrackCandidate, disc: int) -> TrackCandidate:
    """The same candidate, placed on a given disc."""
    return TrackCandidate(
        file_name=candidate.file_name,
        source=candidate.source,
        duration_ms=candidate.duration_ms,
        sample_rate=candidate.sample_rate,
        bit_depth=candidate.bit_depth,
        tag_disc=disc,
        tag_track=candidate.tag_track,
        tag_title=candidate.tag_title,
        artists=candidate.artists,
    )


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
    return _with_disc(candidate, folder_disc)


def _place_bonus_discs(group: _Group) -> None:
    """Give a bonus folder's tracks a disc where nothing has said which.

    The tags are believed where they say, since the folder name gave no number
    to contradict them and they are then the only statement there is. Where
    they say nothing either, the tracks go on the disc after everything else
    the album holds. A bonus disc is never the first one; leaving them on it
    would collide with the album proper track for track.
    """
    unplaced = [
        position
        for position in group.bonus_positions
        if group.candidates[position].tag_disc is None
    ]
    if not unplaced:
        return
    bonus = set(group.bonus_positions)
    held = [
        group.candidates[position].tag_disc or FIRST_DISC
        for position in range(len(group.candidates))
        if position not in bonus
    ]
    disc = max(held, default=FIRST_DISC) + 1
    for position in unplaced:
        group.candidates[position] = _with_disc(group.candidates[position], disc)


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
                bonus_positions=[],
            )
            groups[key] = group
        if (
            folder_disc is not None
            and entry.candidate.tag_disc is not None
            and entry.candidate.tag_disc != folder_disc
        ):
            group.disc_conflicts.append(entry.candidate.file_name)
        if is_unnumbered_bonus(entry.folder_name):
            group.bonus_positions.append(len(group.candidates))
        group.candidates.append(_apply_folder_disc(entry.candidate, folder_disc))
        group.albums.append(normalise(entry.album))
        artist = normalise(entry.album_artist)
        group.artists.append(artist)
        if artist:
            group.tagged_artists += 1
        group.dates.append(normalise(entry.date))
        group.genres.append(normalise(entry.genre))
    return groups


def _paths_by_name(group: _Group) -> dict[str, tuple[str, ...]]:
    """Which files a group's file names stand for.

    A finding names the FILE NAMES it is about while an override pins a full
    path, so the two have to be introduced. One name can stand for more than one
    file: a multi-disc album merged from CD1 and CD2 may hold "01 Intro.flac" in
    both, so this maps to every file that wears the name rather than to one.
    """
    found: dict[str, list[str]] = {}
    for candidate in group.candidates:
        found.setdefault(candidate.file_name, []).append(candidate.source.path)
    return {name: tuple(paths) for name, paths in found.items()}


def _is_answered(
    issue: LibraryIssue,
    album: str,
    accepted: overrides.AcceptedIndex,
    by_name: dict[str, tuple[str, ...]],
) -> bool:
    """Whether this finding has been accepted and so has stopped being one.

    A kind that proposes no value can never be answered, so it is reported at
    every start however long it has been read: there is nothing to accept.
    """
    field = overrides.FIELD_FOR_KIND.get(issue.kind)
    if field is None:
        return False
    paths = tuple(path for name in issue.paths for path in by_name.get(name, ()))
    return overrides.covers(accepted, album, field, paths)


def assemble_albums(
    entries: tuple[SourceEntry, ...],
    accepted: tuple[overrides.Override, ...] = (),
) -> tuple[tuple[Album, ...], tuple[LibraryIssue, ...]]:
    """Group scanned sources into ordered albums, reporting what was inferred.

    The accepted corrections are the third layer, laid over the rules rather
    than replacing them: the tracks are resolved exactly as they always were,
    then whatever has been accepted is applied on top and the findings that have
    been answered stop being reported. Passing none is the old behaviour
    exactly, which is what a library nobody has accepted anything in gets.
    """
    groups = _collect(entries)
    built: list[tuple[AlbumIdentity, Album]] = []
    issues: list[LibraryIssue] = []
    pinned = overrides.index(accepted)

    for group in groups.values():
        _place_bonus_discs(group)
        identity = _identity_of(group)
        label = identity.label
        tracks, track_issues = resolve_tracks(
            tuple(group.candidates), label, identity.handle
        )
        found = list(track_issues)
        if group.disc_conflicts:
            found.append(
                LibraryIssue(
                    kind=IssueKind.DISC_NUMBER_CONFLICT,
                    album=label,
                    detail=f"{len(group.disc_conflicts)} file(s)",
                    paths=tuple(group.disc_conflicts),
                    album_key=identity.handle,
                )
            )
        if not group.tagged_artists:
            found.append(
                LibraryIssue(
                    kind=IssueKind.MISSING_ALBUM_ARTIST,
                    album=label,
                    detail=f"{len(group.candidates)} file(s)",
                    album_key=identity.handle,
                )
            )
        by_name = _paths_by_name(group)
        issues.extend(
            issue
            for issue in found
            if not _is_answered(issue, identity.handle, pinned, by_name)
        )
        # Sorted again after the pins, since one may have moved a track to
        # another number or another disc, which is exactly where it belongs in
        # the album rather than where the rule first put it.
        laid = sorted(
            overrides.applied(tracks, identity.handle, pinned),
            key=lambda item: item.ordering_key,
        )
        built.append(
            (
                identity,
                Album(
                    identity=identity,
                    tracks=tuple(laid),
                    genre=_most_common(group.genres),
                ),
            )
        )

    built.sort(key=lambda pair: pair[0].sort_key)
    return tuple(album for _, album in built), tuple(issues)
