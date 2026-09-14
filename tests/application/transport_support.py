"""The album the transport tests are driven against.

Shared by the transport's own tests and by the shuffle tests beside them. The
device they drive is the recording player every suite shares.
"""

from __future__ import annotations

from stellody.domain.album import Album
from stellody.domain.identity import AlbumIdentity
from stellody.domain.track import CD_SAMPLE_RATE, Track, TrackSource


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
