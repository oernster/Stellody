"""Which rates a library's lossless songs are at.

What the window judges a sound device against when no song is in hand, ruled
by Oliver on 2026-09-18: the exclusive switch is offered only where the device
takes the rate of at least one lossless song the library holds. A lossy song
is never a reason to offer it, so its rate does not count.
"""

from __future__ import annotations

from stellody.domain.album import Album, lossless_rates
from stellody.domain.identity import AlbumIdentity
from stellody.domain.track import CD_SAMPLE_RATE, Track, TrackSource

STUDIO_RATE = 48000
HI_RES_RATE = 96000
DEPTH = 16
NO_DEPTH = 0


def song(number: int, rate: int, depth: int) -> Track:
    """One track at that rate and stated depth."""
    return Track(
        source=TrackSource(path=f"{number}.flac"),
        disc_number=1,
        track_number=number,
        title=f"Track {number}",
        artists=("Holst",),
        duration_ms=1000,
        sample_rate=rate,
        bit_depth=depth,
    )


def album(*tracks: Track) -> Album:
    """One album holding those tracks."""
    return Album(
        identity=AlbumIdentity(album_artist="Holst", title="The Planets"),
        tracks=tracks,
    )


def test_every_lossless_rate_is_named_once() -> None:
    held = (
        album(song(1, CD_SAMPLE_RATE, DEPTH), song(2, CD_SAMPLE_RATE, DEPTH)),
        album(song(1, HI_RES_RATE, DEPTH)),
    )
    assert lossless_rates(held) == frozenset({CD_SAMPLE_RATE, HI_RES_RATE})


def test_a_lossy_song_does_not_count() -> None:
    held = (album(song(1, CD_SAMPLE_RATE, DEPTH), song(2, STUDIO_RATE, NO_DEPTH)),)
    assert lossless_rates(held) == frozenset({CD_SAMPLE_RATE})


def test_an_empty_library_names_nothing() -> None:
    assert lossless_rates(()) == frozenset()
