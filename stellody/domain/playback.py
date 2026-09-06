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


class RepeatMode(Enum):
    """What the end of a track means, when there is a choice about it.

    OFF stops at the last track of the queue. ALBUM carries the end round to
    the start, so the record plays again. ONE holds the track that is playing
    and plays it once more, which is a different question from what the queue
    does: it never advances at all.
    """

    OFF = "off"
    ALBUM = "album"
    ONE = "one"

    @property
    def repeats(self) -> bool:
        """True while an ending is a beginning rather than a stop."""
        return self is not RepeatMode.OFF

    @property
    def after(self) -> RepeatMode:
        """The mode one press of the switch moves to, coming back to OFF.

        Taken from the order these are declared in rather than from a table
        beside them, so the cycle cannot come to disagree with the members it
        is cycling through.
        """
        order = tuple(RepeatMode)
        return order[(order.index(self) + 1) % len(order)]


class OutputMode(Enum):
    """How the stream reaches the device.

    SHARED goes through the system's own mixer, which converts whatever it is
    given and always opens. EXCLUSIVE bypasses the mixer, so it delivers the
    track's own rate untouched; the device may refuse it outright, while a
    platform reached through its mixer alone offers it nowhere.
    """

    SHARED = "shared"
    EXCLUSIVE = "exclusive"


class PlaybackError(RuntimeError):
    """A track could not be opened or played.

    Named in the domain rather than in whichever infrastructure raises it, so
    the application can catch a failure without importing the layer it came
    from. A file that has gone, a format nothing here decodes and a device that
    will not open are one thing to a listener: this track is not playing,
    so they are owed the reason rather than silence.
    """


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
        # Nought is a real answer here, not a missing one: a lossy file has no
        # bit depth to state, so demanding a positive number would mean
        # inventing one on its behalf. `SourceRecord.bit_depth` already
        # defaults to nought for the same reason. A negative depth is still
        # nonsense and still refused.
        if self.bit_depth < 0:
            raise ValueError("bit depth cannot be negative")
        if self.channels <= 0:
            raise ValueError("channel count must be positive")

    @property
    def states_depth(self) -> bool:
        """Whether the source says what bit depth it holds.

        A lossless file does; a lossy one has none to say. The difference
        decides what an exclusive stream could honestly claim, so it is asked
        here rather than inferred from a nought somewhere downstream.
        """
        return self.bit_depth > 0

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
        """True when the device took the track's own bit depth or better.

        A source stating no depth has no native depth to have been taken, so
        this is False rather than trivially true. Left as a comparison against
        nought it would pass for every lossy file ever opened.
        """
        return self.request.states_depth and self.bit_depth >= self.request.bit_depth

    @property
    def is_bit_perfect(self) -> bool:
        """True only when nothing between the file and the device altered it.

        Shared mode is never bit perfect: the mixer resamples by definition,
        which is the whole reason the exclusive toggle exists.

        Neither is a lossy file, whatever the device does. What comes out of
        an MP3 decoder is already not what went into the encoder, so no way of
        opening the device can make the claim true. `depth_is_native` is what
        refuses it, since such a file states no depth to be native to.
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


@dataclass(frozen=True, slots=True)
class Loudness:
    """A chosen level and a mute switch, which are two separate answers.

    A level chosen while muted is kept without breaking the silence: mute is
    a switch of its own, so nothing but that switch turns it off. Held as a
    value so a level chosen before anything is loaded still applies to
    whatever is loaded next.
    """

    level: float = UNITY_VOLUME
    muted: bool = False

    @property
    def audible(self) -> float:
        """What a device is actually asked for: nothing at all while muted."""
        return SILENT_VOLUME if self.muted else self.level

    def at(self, level: float) -> Loudness:
        """The same switch at a different level."""
        return Loudness(level=level, muted=self.muted)

    def silenced(self, muted: bool) -> Loudness:
        """The same level, silenced or given back."""
        return Loudness(level=self.level, muted=muted)


def audible_position(reported: PlaybackPosition, lead_frames: int) -> PlaybackPosition:
    """The position a listener would say, from the one the decode reports.

    A device is handed frames before they are heard, so the decode runs ahead
    of the speakers by whatever is still sitting in the buffer. Shown raw, a
    progress display sits ahead of the music by that much and a track appears
    to finish before it has.
    """
    return PlaybackPosition(
        frame=max(0, reported.frame - lead_frames),
        frame_count=reported.frame_count,
        sample_rate=reported.sample_rate,
    )
