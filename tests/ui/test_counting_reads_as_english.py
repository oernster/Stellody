"""A row says "1 track", never "1 tracks".

Found on the site's own screenshot of the list view, where a single track
album read "1997  Pop  1 tracks". Both counts on an album row were written
plural whatever they held, so any album or disc holding one of something said
it the wrong way round in front of everybody.
"""

from __future__ import annotations

from stellody.domain.album import Album
from stellody.domain.identity import AlbumIdentity
from stellody.domain.track import CD_SAMPLE_RATE, Track, TrackSource
from stellody.ui.nodes import Node
from stellody.ui.row_text import Column, text_for


def _track(number: int) -> Track:
    """One ordinary track of an album."""
    return Track(
        source=TrackSource(path=f"{number}.flac"),
        disc_number=1,
        track_number=number,
        title=f"Track {number}",
        artists=("Apollo 440",),
        duration_ms=1000,
        sample_rate=CD_SAMPLE_RATE,
        bit_depth=16,
    )


def _detail(*tracks: Track) -> str:
    """The detail cell of an album row holding these tracks."""
    album = Album(
        identity=AlbumIdentity(album_artist="Apollo 440", title="Electro Glide"),
        tracks=tracks,
    )
    return text_for(Node(row=0, parent=None, album=album), Column.DETAIL)


class TestAnAlbumRow:
    def test_one_track_is_singular(self) -> None:
        """The whole of what this is for."""
        assert "1 track" in _detail(_track(1))
        assert "1 tracks" not in _detail(_track(1))

    def test_more_than_one_stays_plural(self) -> None:
        """The ordinary case must not be broken to fix the other."""
        assert "2 tracks" in _detail(_track(1), _track(2))
