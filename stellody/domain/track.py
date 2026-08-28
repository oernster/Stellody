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
        if self.bit_depth <= 0:
            raise ValueError("bit depth must be positive")

    @property
    def ordering_key(self) -> tuple[int, int, str]:
        """Where this track sits within its album."""
        return (self.disc_number, self.track_number, sort_key(self.title))

    @property
    def artist_text(self) -> str:
        """Every artist on this track, joined for display."""
        return ", ".join(self.artists)

    @property
    def is_high_resolution(self) -> bool:
        """True when the track exceeds CD rate or depth."""
        return self.sample_rate > CD_SAMPLE_RATE or self.bit_depth > CD_BIT_DEPTH
