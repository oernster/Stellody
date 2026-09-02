"""Deciding a track's place in its album when the tags disagree.

Tags are primary. Where two tracks in one album claim the same disc and track
number, the leading number in the file name is the tiebreaker, because in every
observed case of tag damage the file names remained correct and distinct.
The workaround is reported as a library issue rather than hidden.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from stellody.domain.album import FIRST_DISC
from stellody.domain.health import IssueKind, LibraryIssue
from stellody.domain.text import (
    comparison_key,
    filename_ordinal,
    filename_title,
    normalise,
)
from stellody.domain.track import Track, TrackSource

UNKNOWN_ARTIST = "Unknown Artist"


@dataclass(frozen=True, slots=True)
class TrackCandidate:
    """One audio source plus whatever its tags claimed, before adjudication."""

    file_name: str
    source: TrackSource
    duration_ms: int
    sample_rate: int
    bit_depth: int
    tag_disc: int | None = None
    tag_track: int | None = None
    tag_title: str = ""
    artists: tuple[str, ...] = ()


def _next_free(used: set[int]) -> int:
    """The lowest track number not already taken on a disc."""
    number = 1
    while number in used:
        number += 1
    return number


def _tagged_keys(
    candidates: tuple[TrackCandidate, ...],
) -> dict[int, tuple[int, int]]:
    """The disc and track number each candidate claims, where it claims one."""
    keys: dict[int, tuple[int, int]] = {}
    for position, candidate in enumerate(candidates):
        if candidate.tag_track is not None:
            disc = candidate.tag_disc if candidate.tag_disc else FIRST_DISC
            keys[position] = (disc, candidate.tag_track)
    return keys


def _duplicate_titles(candidates: tuple[TrackCandidate, ...]) -> set[str]:
    """Titles claimed by more than one candidate in the same album."""
    counts = Counter(
        comparison_key(candidate.tag_title)
        for candidate in candidates
        if candidate.tag_title
    )
    return {title for title, count in counts.items() if count > 1}


def _chosen_title(
    candidate: TrackCandidate, trusted: bool, duplicates: set[str]
) -> tuple[str, bool]:
    """The title to use, plus whether the tag had to be set aside."""
    tagged = normalise(candidate.tag_title)
    if not tagged:
        return filename_title(candidate.file_name), True
    if not trusted and comparison_key(tagged) in duplicates:
        return filename_title(candidate.file_name), False
    return tagged, False


def resolve_tracks(
    candidates: tuple[TrackCandidate, ...],
    album_label: str,
    album_key: str = "",
) -> tuple[tuple[Track, ...], tuple[LibraryIssue, ...]]:
    """Turn candidates into ordered tracks, reporting what had to be worked out.

    Candidates whose tags are unambiguous keep them. Candidates that collide or
    that carry no track number are placed from their file names instead.
    """
    if not candidates:
        return (), ()

    issues: list[LibraryIssue] = []
    keys = _tagged_keys(candidates)
    counts = Counter(keys.values())
    colliding = {key for key, count in counts.items() if count > 1}
    duplicates = _duplicate_titles(candidates)
    order = sorted(range(len(candidates)), key=lambda i: candidates[i].file_name)

    for key in sorted(colliding):
        affected = tuple(candidates[i].file_name for i in order if keys.get(i) == key)
        issues.append(
            LibraryIssue(
                kind=IssueKind.DUPLICATE_TRACK_NUMBER,
                album=album_label,
                album_key=album_key,
                detail=f"disc {key[0]}, track {key[1]}",
                paths=affected,
            )
        )

    resolved: dict[int, tuple[int, int]] = {}
    used: dict[int, set[int]] = {}
    for position in order:
        key = keys.get(position)
        if key is not None and key not in colliding:
            resolved[position] = key
            used.setdefault(key[0], set()).add(key[1])

    untagged: list[str] = []
    for position in order:
        if position in resolved:
            continue
        candidate = candidates[position]
        file_disc, file_track = filename_ordinal(candidate.file_name)
        tagged_disc = candidate.tag_disc if candidate.tag_disc else FIRST_DISC
        disc = file_disc if file_disc is not None else tagged_disc
        taken = used.setdefault(disc, set())
        if file_track is None:
            untagged.append(candidate.file_name)
            track = _next_free(taken)
        elif file_track in taken:
            track = _next_free(taken)
        else:
            track = file_track
        resolved[position] = (disc, track)
        taken.add(track)

    if untagged:
        issues.append(
            LibraryIssue(
                kind=IssueKind.MISSING_TRACK_NUMBER,
                album=album_label,
                album_key=album_key,
                detail=f"{len(untagged)} file(s)",
                paths=tuple(untagged),
            )
        )

    tracks: list[Track] = []
    missing_titles: list[str] = []
    for position in order:
        candidate = candidates[position]
        disc, track = resolved[position]
        trusted = keys.get(position) is not None and keys[position] not in colliding
        title, was_missing = _chosen_title(candidate, trusted, duplicates)
        if was_missing:
            missing_titles.append(candidate.file_name)
        artists = candidate.artists if candidate.artists else (UNKNOWN_ARTIST,)
        tracks.append(
            Track(
                source=candidate.source,
                disc_number=disc,
                track_number=track,
                title=title,
                artists=artists,
                duration_ms=candidate.duration_ms,
                sample_rate=candidate.sample_rate,
                bit_depth=candidate.bit_depth,
            )
        )

    if missing_titles:
        issues.append(
            LibraryIssue(
                kind=IssueKind.MISSING_TITLE,
                album=album_label,
                album_key=album_key,
                detail=f"{len(missing_titles)} file(s)",
                paths=tuple(missing_titles),
            )
        )

    tracks.sort(key=lambda item: item.ordering_key)
    return tuple(tracks), tuple(issues)
