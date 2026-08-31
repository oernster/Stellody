"""Showing the rating of the track the position row is about, then setting it.

It is about the track being pointed at, falling back to the one playing where
nothing is. That is deliberately not the rule the shape beside it follows: a
shape is a reading of what is audible, while the stars are a control somebody
acts on; a control has to be about the thing under the hand.

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
from stellody.domain.listening import NO_STARS, album_handle, track_handle
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

    def show_album_rating(self) -> None:
        """Show the rating the open album carries, without reporting one."""
        album = self._shown_album
        stars = NO_STARS
        if album is not None:
            stars = self._listening.of(album_handle(album.identity)).stars
        self._album_pane.show_album_stars(stars)

    def rate_album(self, stars: int) -> None:
        """Give the open album a rating of its own.

        Its own rather than one worked out from its tracks: a record with one
        poor track on it is not a poor record, so an album is judged whole or
        it is not judged at all.
        """
        album = self._shown_album
        if album is None:
            return
        self._listening.rate(
            album_handle(album.identity),
            album.ordered_tracks()[0].source.path,
            stars,
        )

    def _rated(self) -> tuple[Album, Track] | None:
        """The album and track the stars are about; None when about none.

        What is HIGHLIGHTED wins, which is where this parts from the shape
        drawn under the line beside it. The shape belongs to what is audible,
        so playback owns it; the stars are a control somebody acts on, so they
        belong to whatever is being pointed at. Otherwise a track picked out
        while something else played could not be rated at all: the stars would
        answer for the music instead.

        The two agree throughout ordinary listening anyway, since the
        highlight follows playback from track to track. They part only where
        somebody has deliberately moved off it.
        """
        where = self.highlighted()
        track = self._model.track_at(where)
        album = self._model.album_at(where)
        if track is not None and album is not None:
            return album, track
        playing = self._transport.current
        queued = self._transport.album
        if playing is None or queued is None:
            return None
        return queued, playing


def _handle(album: Album, track: Track) -> str:
    """What this track's record is kept against."""
    return track_handle(album.identity, track.disc_number, track.track_number)
