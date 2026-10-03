"""Rating a track from its row, counting a track that plays out, rating an album.

A track is rated where it is listed: a column of stars beside its plays, in the
list and in the album opened under the sleeves alike. It used to be rated from
stars on the row under the library, which followed one track at a time; moved
on 2026-09-16, as Oliver asked. The column says every track's rating at once
and needs nothing highlighted first. See `star_cells.py` for the two gestures.

A record is kept against the album's identity with the disc and track number
under it, so the album has to be in hand before the rating can be. A row is an
index the model can answer for directly, so nothing asks the model to find a
track it was already handed, which matters more than it looks: that search is
retried when it misses, so a second caller would consume the attempt the first
one needed.

The play count still rides on the row under the library as well. It follows
what is highlighted, falling back to the one playing where nothing is.
"""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QModelIndex

from stellody.application.listening import ListeningUnwritable
from stellody.domain.album import Album
from stellody.domain.listening import NO_STARS, album_handle, track_handle
from stellody.domain.track import Track
from stellody.ui.palette import Mode
from stellody.ui.settings_keys import STATUS_TIMEOUT_MS
from stellody.ui.star_cells import RatingKeys

# Said where the library file will not take a write, in the words the shop
# list uses for the same thing. Nothing is held that was not written, so
# "nothing has changed" is true of the screen as well as the disk.
RATING_NOT_SAVED = "That rating could not be saved, so nothing has changed."
PLAY_NOT_SAVED = "That play could not be counted, so nothing has changed."


class Rating:
    """The window's half of showing and setting a rating."""

    def start_rating(self) -> None:
        """Let every list of tracks take a rating, by a press or by a number."""
        self._rating_keys = RatingKeys(self.rate_track, self)
        for view in self._track_views():
            view.itemDelegate().rated.connect(self.rate_track)
            view.installEventFilter(self._rating_keys)

    def show_rating_appearance(self, mode: Mode) -> None:
        """Draw every column of stars in the appearance the window is wearing."""
        for view in self._track_views():
            view.itemDelegate().show_appearance(mode)
            view.viewport().update()

    def _track_views(self) -> tuple:
        """Every view a track is listed in: the list, then the open album's."""
        return (self._tree, *self._album_pane.columns)

    def rate_track(self, where: QModelIndex, stars: int) -> bool:
        """Give the track on this row a rating; answer whether there was one."""
        track = self._model.track_at(where)
        album = self._model.album_at(where)
        if track is None or album is None:
            return False
        handle = _handle(album, track)
        self._kept(
            lambda: self._listening.rate(handle, track.source.path, stars),
            RATING_NOT_SAVED,
        )
        # Redrawn either way: a refused rating is drawn as what is held.
        self._model.redraw_listening(handle)
        return True

    def follow_plays(self) -> None:
        """Show the play count of what is highlighted, else of what is loaded."""
        shown = self._shown()
        if shown is None:
            self._position_bar.show_plays(None)
            return
        self._position_bar.show_plays(self._listening.of(_handle(*shown)))

    def count_play(self, album: Album, track: Track) -> None:
        """Record that a track played out.

        Told by the transport, which is the only thing that can tell an ending
        from a track somebody skipped. It is told the album with it, so nothing
        has to go looking for a track a rescan may since have replaced.
        """
        handle = _handle(album, track)
        if not self._kept(
            lambda: self._listening.count_play(handle, track.source.path),
            PLAY_NOT_SAVED,
        ):
            return
        self._model.redraw_listening(handle)
        self.follow_plays()

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
        kept = self._kept(
            lambda: self._listening.rate(
                album_handle(album.identity),
                album.ordered_tracks()[0].source.path,
                stars,
            ),
            RATING_NOT_SAVED,
        )
        if not kept:
            # The stars already show what was pressed; put back what is held.
            self.show_album_rating()

    def _kept(self, write: Callable[[], object], refused: str) -> bool:
        """Make one write; say so on the status line where it was refused.

        Caught here rather than left to rise, since an exception raised inside
        a Qt slot ends the slot in silence, which is exactly the failure this
        exists to put into words.
        """
        try:
            write()
        except ListeningUnwritable:
            self.statusBar().showMessage(refused, STATUS_TIMEOUT_MS)
            return False
        return True

    def _shown(self) -> tuple[Album, Track] | None:
        """The album and track the play count is about; None when about none.

        What is HIGHLIGHTED wins, falling back to what is playing. The two
        agree throughout ordinary listening anyway, since the highlight
        follows playback from track to track.
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
