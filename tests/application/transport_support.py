"""The album and the device the transport tests are driven against.

Shared by the transport's own tests and by the shuffle tests beside them. The
player is hand written rather than a mock, so what is asserted is the sequence
of commands the transport issued to a device that recorded them.
"""

from __future__ import annotations

from stellody.domain.album import Album
from stellody.domain.identity import AlbumIdentity
from stellody.domain.playback import (
    UNITY_VOLUME,
    OutputMode,
    OutputReport,
    OutputRequest,
    PlaybackPosition,
    PlaybackState,
)
from stellody.domain.track import (
    CD_SAMPLE_RATE,
    MILLISECONDS_PER_SECOND,
    Track,
    TrackSource,
)

# Long enough that any elapsed time a test names falls inside the track.
SECONDS_PER_TEST_TRACK = 600


def track(number: int) -> Track:
    """One ordinary track of an album."""
    return Track(
        source=TrackSource(path=f"{number}.flac"),
        disc_number=1,
        track_number=number,
        title=f"Track {number}",
        artists=("Holst",),
        duration_ms=1000,
        sample_rate=CD_SAMPLE_RATE,
        bit_depth=16,
    )


def album_of(*tracks: Track) -> Album:
    """An album holding these tracks."""
    return Album(
        identity=AlbumIdentity(album_artist="Holst", title="The Planets"),
        tracks=tracks,
    )


def reversed_order(tracks: tuple[Track, ...]) -> tuple[Track, ...]:
    """A shuffle that is not random, so what it did can be asserted.

    A stand-in for the real scatter, which is random.sample and so cannot be
    written down in an assertion. What it stands in for is a permutation, not
    a reversal: any test whose result would differ under a different
    permutation is testing this function rather than the transport.
    """
    return tuple(reversed(tracks))


class FakePlayer:
    """A playback port that records rather than plays."""

    def __init__(self) -> None:
        self.calls: list[str] = []
        self.loaded: list[TrackSource] = []
        self.requests: list[OutputRequest] = []
        self.state = PlaybackState.STOPPED
        self.finished = False
        self.volume = UNITY_VOLUME
        # None until a test says how far in it is, because a device that has
        # not been asked to play anything genuinely does not know.
        self.elapsed_ms: int | None = None

    def load(self, source: TrackSource, request: OutputRequest) -> OutputReport:
        """Record the load and report a plain shared stream."""
        self.calls.append("load")
        self.loaded.append(source)
        self.requests.append(request)
        self.finished = False
        self.state = PlaybackState.PAUSED
        return OutputReport(
            request=request,
            mode=OutputMode.SHARED,
            sample_rate=request.sample_rate,
            bit_depth=request.bit_depth,
        )

    def play(self) -> None:
        """Record the play."""
        self.calls.append("play")
        self.state = PlaybackState.PLAYING

    def pause(self) -> None:
        """Record the pause."""
        self.calls.append("pause")
        self.state = PlaybackState.PAUSED

    def stop(self) -> None:
        """Record the stop."""
        self.calls.append("stop")
        self.state = PlaybackState.STOPPED

    def seek(self, frame: int) -> None:
        """Record the seek."""
        self.calls.append(f"seek {frame}")

    def position(self) -> PlaybackPosition | None:
        """How far in, once a test has said; nothing until then."""
        if self.elapsed_ms is None:
            return None
        return PlaybackPosition(
            frame=self.elapsed_ms * CD_SAMPLE_RATE // MILLISECONDS_PER_SECOND,
            frame_count=CD_SAMPLE_RATE * SECONDS_PER_TEST_TRACK,
            sample_rate=CD_SAMPLE_RATE,
        )

    def set_volume(self, level: float) -> None:
        """Record the level asked for."""
        self.volume = level
