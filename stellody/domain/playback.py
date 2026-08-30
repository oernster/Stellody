"""What playback is, stated without reference to any audio library.

The distinction this module exists to hold is between what Stellody ASKED the
output device for and what it actually GOT. On the reference hardware those two
differ: the onboard device accepts 44.1, 48, 96 and 192 kHz in exclusive mode
yet its native sample format at every one of them is 16 bit, so a 24 bit FLAC
reaches it truncated. A player that reports "exclusive" and leaves it there is
claiming something it has not delivered, so an achieved output is a separate
value from a requested one and it carries whether the stream was bit perfect.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from stellody.domain.track import MILLISECONDS_PER_SECOND

STEREO_CHANNELS = 2

# Gain is a property of playback rather than of the device that produces it, so
# the two ends of the range are stated here and every layer means the same two.
UNITY_VOLUME = 1.0
SILENT_VOLUME = 0.0


class PlaybackState(Enum):
    """Where the transport is. Nothing else is a state."""

    STOPPED = "stopped"
    PLAYING = "playing"
    PAUSED = "paused"

    @property
    def is_active(self) -> bool:
        """True when a track is loaded, whether or not it is advancing."""
        return self is not PlaybackState.STOPPED


class OutputMode(Enum):
    """How the stream reaches the device.

    SHARED goes through the Windows mixer, which resamples whatever it is given
    and always opens. EXCLUSIVE bypasses the mixer, so it delivers the track's
    own rate untouched; the device may refuse it outright.
    """

    SHARED = "shared"
    EXCLUSIVE = "exclusive"


@dataclass(frozen=True, slots=True)
class OutputRequest:
    """The stream Stellody asks for, before any device has been consulted."""

    sample_rate: int
    bit_depth: int
    mode: OutputMode = OutputMode.SHARED
    channels: int = STEREO_CHANNELS

    def __post_init__(self) -> None:
        if self.sample_rate <= 0:
            raise ValueError("sample rate must be positive")
        if self.bit_depth <= 0:
            raise ValueError("bit depth must be positive")
        if self.channels <= 0:
            raise ValueError("channel count must be positive")

    def as_shared(self) -> OutputRequest:
        """The same stream asked for through the mixer instead."""
        return OutputRequest(
            sample_rate=self.sample_rate,
            bit_depth=self.bit_depth,
            mode=OutputMode.SHARED,
            channels=self.channels,
        )


@dataclass(frozen=True, slots=True)
class OutputReport:
    """The stream actually opened; the honest reading of what it delivers."""

    request: OutputRequest
    mode: OutputMode
    sample_rate: int
    bit_depth: int
    fallback_reason: str = ""

    def __post_init__(self) -> None:
        if self.sample_rate <= 0:
            raise ValueError("sample rate must be positive")
        if self.bit_depth <= 0:
            raise ValueError("bit depth must be positive")

    @property
    def rate_is_native(self) -> bool:
        """True when the device took the track's own sample rate."""
        return self.sample_rate == self.request.sample_rate

    @property
    def depth_is_native(self) -> bool:
        """True when the device took the track's own bit depth or better."""
        return self.bit_depth >= self.request.bit_depth

    @property
    def is_bit_perfect(self) -> bool:
        """True only when nothing between the file and the device altered it.

        Shared mode is never bit perfect: the mixer resamples by definition,
        which is the whole reason the exclusive toggle exists.
        """
        return (
            self.mode is OutputMode.EXCLUSIVE
            and self.rate_is_native
            and self.depth_is_native
        )

    @property
    def fell_back(self) -> bool:
        """True when the device refused the mode that was asked for."""
        return self.mode is not self.request.mode


SECONDS_PER_MINUTE = 60


def clock_text(frames: int, sample_rate: int) -> str:
    """`frames` at `sample_rate` as minutes and seconds, for a display.

    Seconds are truncated rather than rounded, so a figure never names a
    second the track has not reached. Minutes are not padded, because a
    listener reads 3:07 and not 03:07.
    """
    if sample_rate <= 0:
        raise ValueError("sample rate must be positive")
    total = max(0, frames) // sample_rate
    return f"{total // SECONDS_PER_MINUTE}:{total % SECONDS_PER_MINUTE:02d}"


@dataclass(frozen=True, slots=True)
class PlaybackPosition:
    """How far into a track the transport has reached."""

    frame: int
    frame_count: int
    sample_rate: int

    def __post_init__(self) -> None:
        if self.frame < 0:
            raise ValueError("frame cannot be negative")
        if self.frame_count < 0:
            raise ValueError("frame count cannot be negative")
        if self.sample_rate <= 0:
            raise ValueError("sample rate must be positive")

    @property
    def elapsed_ms(self) -> int:
        """Milliseconds played so far."""
        return self.frame * MILLISECONDS_PER_SECOND // self.sample_rate

    @property
    def total_ms(self) -> int:
        """The track's length in milliseconds."""
        return self.frame_count * MILLISECONDS_PER_SECOND // self.sample_rate

    @property
    def remaining_ms(self) -> int:
        """Milliseconds still to play; never negative."""
        return max(0, self.total_ms - self.elapsed_ms)

    @property
    def is_complete(self) -> bool:
        """True once the transport has reached the end of the track."""
        return self.frame >= self.frame_count
