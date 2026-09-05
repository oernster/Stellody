"""Cue-sheet parsing: one audio file described as many tracks.

163 of the 485 albums in the reference library are built from a cue sheet with
cue sheet, so this is a main path rather than an edge case. Parsing is pure
text work; reading the file belongs to infrastructure.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from stellody.domain.text import normalise, split_artists

CD_FRAMES_PER_SECOND = 75
SECONDS_PER_MINUTE = 60
AUDIO_INDEX = 1

# What a ripper writes where the disc was not in its database. They are the
# absence of a name rather than a name, so a sheet carrying one must let the
# file's own tags answer instead of overruling them with a stand-in. Measured
# across the reference library: 2 of its 171 sheets carry these, both from
# discs the ripper could not identify; both reported the album, the artist
# and every track title as unknown while the files themselves were tagged.
PLACEHOLDER_NAMES = frozenset({"unknown", "unknown artist", "unknown title"})

# A track named only by its own position, which is what the same ripper writes
# where it has no track names. It states nothing the number has not already
# said, so it is no more a title than the names above are names.
_NUMBERED_ONLY = re.compile(r"^track\s*0*\d+$", re.IGNORECASE)


def _a_name(value: str) -> str:
    """The value; empty where it is a stand-in for a name rather than one."""
    return "" if value.casefold() in PLACEHOLDER_NAMES else value


def _a_track_name(value: str) -> str:
    """A track's title; empty where it only restates the track number."""
    return "" if _NUMBERED_ONLY.match(value) else _a_name(value)


@dataclass(frozen=True, slots=True)
class CueTrack:
    """One track as described by a cue sheet."""

    number: int
    title: str
    performers: tuple[str, ...]
    file_name: str
    start_frame: int
    end_frame: int | None = None


@dataclass(frozen=True, slots=True)
class CueSheet:
    """A parsed cue sheet: album level data plus its tracks."""

    album_title: str
    album_performer: str
    tracks: tuple[CueTrack, ...]
    date: str = ""
    genre: str = ""

    @property
    def file_names(self) -> tuple[str, ...]:
        """Every audio file the sheet refers to, first appearance order."""
        seen: dict[str, None] = {}
        for track in self.tracks:
            seen.setdefault(track.file_name, None)
        return tuple(seen)


class CueParseError(ValueError):
    """Raised when a cue sheet cannot be understood."""


def timestamp_to_frames(timestamp: str, sample_rate: int) -> int:
    """Convert a cue MM:SS:FF timestamp into sample frames.

    Cue sheets count in CD frames of 1/75 second. Every sample rate Stellody
    meets divides by 75 exactly, so this stays integer arithmetic.
    """
    parts = timestamp.split(":")
    if len(parts) != 3:
        raise CueParseError(f"malformed timestamp: {timestamp!r}")
    try:
        minutes, seconds, frames = (int(part) for part in parts)
    except ValueError as error:
        raise CueParseError(f"malformed timestamp: {timestamp!r}") from error
    if minutes < 0 or seconds < 0 or frames < 0:
        raise CueParseError(f"negative timestamp: {timestamp!r}")
    total = (minutes * SECONDS_PER_MINUTE + seconds) * CD_FRAMES_PER_SECOND + frames
    return total * sample_rate // CD_FRAMES_PER_SECOND


def _split_command(line: str) -> tuple[str, str]:
    """Split a cue line into its command word and remainder."""
    stripped = line.strip()
    if not stripped:
        return "", ""
    parts = stripped.split(None, 1)
    return parts[0].upper(), parts[1] if len(parts) > 1 else ""


def _unquote(value: str) -> str:
    """Strip the surrounding quotes a cue sheet puts around free text."""
    trimmed = value.strip()
    if len(trimmed) >= 2 and trimmed[0] == '"':
        closing = trimmed.find('"', 1)
        if closing > 0:
            return trimmed[1:closing]
    return trimmed


def _file_name(value: str) -> str:
    """The audio file named by a FILE line, without its format word."""
    trimmed = value.strip()
    if trimmed.startswith('"'):
        return _unquote(trimmed)
    parts = trimmed.rsplit(None, 1)
    return parts[0] if len(parts) == 2 else trimmed


@dataclass(slots=True)
class _Pending:
    """Mutable state for a track while its lines are still being read."""

    number: int
    title: str = ""
    performers: tuple[str, ...] = ()
    file_name: str = ""
    start_frame: int | None = None


def _finish(pending: list[_Pending], fallback_title: str) -> tuple[CueTrack, ...]:
    """Turn accumulated track state into immutable tracks with end frames."""
    placed = [item for item in pending if item.start_frame is not None]
    tracks: list[CueTrack] = []
    for position, item in enumerate(placed):
        end: int | None = None
        following = placed[position + 1] if position + 1 < len(placed) else None
        if following is not None and following.file_name == item.file_name:
            end = following.start_frame
        tracks.append(
            CueTrack(
                number=item.number,
                title=item.title or f"{fallback_title} {item.number}",
                performers=item.performers,
                file_name=item.file_name,
                start_frame=item.start_frame,
                end_frame=end,
            )
        )
    return tuple(tracks)


def parse_cue(text: str, sample_rate: int) -> CueSheet:
    """Parse cue-sheet text into an album description.

    The sample rate is needed because cue timestamps are in CD frames and the
    resulting sources are addressed in samples.
    """
    if sample_rate <= 0:
        raise CueParseError("sample rate must be positive")
    album_title = ""
    album_performer = ""
    date = ""
    genre = ""
    current_file = ""
    pending: list[_Pending] = []

    for line in text.splitlines():
        command, remainder = _split_command(line)
        if not command:
            continue
        if command == "REM":
            keyword, value = _split_command(remainder)
            if keyword == "DATE":
                date = _unquote(value)
            elif keyword == "GENRE":
                genre = _unquote(value)
        elif command == "FILE":
            current_file = _file_name(remainder)
        elif command == "TRACK":
            parts = remainder.split()
            if not parts or not parts[0].isdigit():
                raise CueParseError(f"malformed TRACK line: {line.strip()!r}")
            pending.append(_Pending(number=int(parts[0]), file_name=current_file))
        elif command == "TITLE":
            if pending:
                pending[-1].title = _a_track_name(normalise(_unquote(remainder)))
            else:
                album_title = _a_name(normalise(_unquote(remainder)))
        elif command == "PERFORMER":
            performer = _a_name(normalise(_unquote(remainder)))
            if pending:
                pending[-1].performers = split_artists(performer)
            else:
                album_performer = performer
        elif command == "INDEX" and pending:
            parts = remainder.split()
            if len(parts) >= 2 and parts[0].isdigit() and int(parts[0]) == AUDIO_INDEX:
                pending[-1].start_frame = timestamp_to_frames(parts[1], sample_rate)

    return CueSheet(
        album_title=album_title,
        album_performer=album_performer,
        tracks=_finish(pending, album_title or "Track"),
        date=date,
        genre=genre,
    )
