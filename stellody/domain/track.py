"""Tracks, plus the slice-of-a-file abstraction they are built on.

A third of the reference library is a single FLAC per album with a sidecar cue
sheet, so a track is not the same thing as a file. TrackSource carries that
distinction and nothing above this module needs to know about it.
"""

from __future__ import annotations

from dataclasses import dataclass

from stellody.domain.text import sort_key

MILLISECONDS_PER_SECOND = 1000
CD_SAMPLE_RATE = 44100
CD_BIT_DEPTH = 16

# The containers that carry a picture alongside the sound. Measured over the
# reference library rather than listed from a manual: every video file in it is
# .m4v, which is the MP4 container the packet reader already opens for M4A,
# holding H.264 beside AAC. A format is claimed only where one has been seen.
#
# This is the one home for that fact. The walk decides what to take, the
# decoder decides which reader opens it and a track decides whether it has a
# picture to show; all three read it from here, so they cannot come to disagree
# about which files carry a picture.
PICTURE_SUFFIXES = frozenset({".m4v"})

# Both separators are answered here because the domain may not import os.path
# and a Windows path reaches it with backslashes.
_PATH_SEPARATORS = ("/", "\\")


def suffix_of(path: str) -> str:
    """The lowercased extension of a path, empty where it has none.

    A name that is nothing but an extension, such as ".flac", is a hidden file
    rather than a suffix, which is what `os.path.splitext` says of it too.
    """
    name = path
    for separator in _PATH_SEPARATORS:
        name = name.rpartition(separator)[2]
    dot = name.rfind(".")
    if dot <= 0:
        return ""
    return name[dot:].casefold()


@dataclass(frozen=True, slots=True)
class TrackSource:
    """A region of an audio file: either the whole of it or one cue-sheet track."""

    path: str
    start_frame: int = 0
    end_frame: int | None = None

    def __post_init__(self) -> None:
        if not self.path:
            raise ValueError("a track source needs a path")
        if self.start_frame < 0:
            raise ValueError("start_frame cannot be negative")
        if self.end_frame is not None and self.end_frame <= self.start_frame:
            raise ValueError("end_frame must be beyond start_frame")

    @property
    def is_slice(self) -> bool:
        """True when this source is part of a file rather than all of it."""
        return self.start_frame > 0 or self.end_frame is not None

    @property
    def carries_picture(self) -> bool:
        """True when this source holds a picture stream as well as sound.

        Read off the path rather than carried as a field, so a source built
        anywhere in the application answers it the same way and no construction
        site can forget to say. The sound path is unaffected either way: a
        video's audio is decoded by exactly the reader its container already
        used, so this says what to SHOW rather than how to play.
        """
        return suffix_of(self.path) in PICTURE_SUFFIXES

    @property
    def frame_count(self) -> int | None:
        """Length in frames; None when the source runs to end of file."""
        if self.end_frame is None:
            return None
        return self.end_frame - self.start_frame

    def duration_ms(self, sample_rate: int) -> int | None:
        """Length in milliseconds at a given sample rate."""
        frames = self.frame_count
        if frames is None or sample_rate <= 0:
            return None
        return frames * MILLISECONDS_PER_SECOND // sample_rate


@dataclass(frozen=True, slots=True)
class Track:
    """One playable track, wherever its audio physically lives."""

    source: TrackSource
    disc_number: int
    track_number: int
    title: str
    artists: tuple[str, ...]
    duration_ms: int
    sample_rate: int
    bit_depth: int

    def __post_init__(self) -> None:
        if self.disc_number < 1:
            raise ValueError("disc numbers start at 1")
        if self.track_number < 1:
            raise ValueError("track numbers start at 1")
        if not self.title:
            raise ValueError("a track needs a title")
        if not self.artists:
            raise ValueError("a track needs at least one artist")
        if self.duration_ms < 0:
            raise ValueError("duration cannot be negative")
        if self.sample_rate <= 0:
            raise ValueError("sample rate must be positive")
        # Nought is the absence of a reading, not a depth of nought: a lossy
        # file states none and the probe reports that honestly rather than
        # inventing a plausible sixteen. Only a negative depth is a value no
        # file could carry. `OutputRequest` draws the same distinction; the
        # two must agree, since a rule enforced in one of them alone is a
        # library that scans but cannot be assembled.
        if self.bit_depth < 0:
            raise ValueError("bit depth cannot be negative")

    @property
    def ordering_key(self) -> tuple[int, int, str]:
        """Where this track sits within its album."""
        return (self.disc_number, self.track_number, sort_key(self.title))

    @property
    def artist_text(self) -> str:
        """Every artist on this track, joined for display."""
        return ", ".join(self.artists)

    @property
    def states_depth(self) -> bool:
        """True when the file stated a bit depth. A lossy one states none."""
        return self.bit_depth > 0

    @property
    def is_high_resolution(self) -> bool:
        """True when the track exceeds CD rate or depth.

        A source that states no depth cannot support the claim, whatever rate
        it decodes at. Opus is the case that forces this: it always decodes at
        48 kHz whatever it was encoded from, so a rate test alone would badge
        every Opus file as better than CD on the strength of a property of the
        codec rather than of the recording.
        """
        if not self.states_depth:
            return False
        return self.sample_rate > CD_SAMPLE_RATE or self.bit_depth > CD_BIT_DEPTH
