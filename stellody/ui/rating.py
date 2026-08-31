"""Showing the rating of the track the position row is about, then setting it.

It follows exactly what the shape below it follows: the track that is loaded,
else the one that is highlighted. One rule for the whole row, so the stars and
the shape are never about two different tracks.

A record is kept against the album's identity with the disc and track number
under it, so the album has to be in hand before the rating can be. Both routes
have one already: the transport holds the album its queue was made from; the
highlight is an index the model can answer for directly. Neither asks the
model to find a track it was already handed, which matters more than it looks:
that search is retried when it misses, so a second caller would consume the
attempt the first one needed.
"""

from __future__ import annotations

from stellody.domain.album import Album
from stellody.domain.listening import track_handle
from stellody.domain.track import Track


class Rating:
    """The window's half of showing and setting a rating."""

    def follow_rating(self) -> None:
        """Show the rating of what is loaded, else of what is highlighted."""
        shown = self._rated()
        if shown is None:
            self._position_bar.show_listening(None)
            return
        self._position_bar.show_listening(self._listening.of(_handle(*shown)))

    def rate_shown(self, stars: int) -> None:
        """Give the track the row is about a rating, then show what it holds."""
        shown = self._rated()
        if shown is None:
            return
        _album, track = shown
        self._listening.rate(_handle(*shown), track.source.path, stars)
        self.follow_rating()

    def count_play(self, album: Album, track: Track) -> None:
        """Record that a track played out.

        Told by the transport, which is the only thing that can tell an ending
        from a track somebody skipped. It is told the album with it, so nothing
        has to go looking for a track a rescan may since have replaced.
        """
        self._listening.count_play(_handle(album, track), track.source.path)
        self.follow_rating()

    def _rated(self) -> tuple[Album, Track] | None:
        """The album and track the row is about; None when it is about none."""
        playing = self._transport.current
        queued = self._transport.album
        if playing is not None and queued is not None:
            return queued, playing
        where = self.highlighted()
        track = self._model.track_at(where)
        album = self._model.album_at(where)
        if track is None or album is None:
            return None
        return album, track


def _handle(album: Album, track: Track) -> str:
    """What this track's record is kept against."""
    return track_handle(album.identity, track.disc_number, track.track_number)
