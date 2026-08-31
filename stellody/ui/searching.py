"""Narrowing what is on screen to what somebody typed.

The filter itself is pure and lives in the domain. This is the half that holds
what a load or a scan produced, hands the phrase to it, then puts the answer
in front of somebody.

**What arrives is remembered whole.** A search narrows a copy, so clearing the
box restores the library without reading a single file and without asking the
store for anything.

**An album is kept whole.** A phrase that hits one track keeps every track, so
the album reads the way it always does. The track it hit is selected as though
it were about to play, then its row is flashed to take the eye to it.
"""

from __future__ import annotations

from PySide6.QtCore import QModelIndex

from stellody.application.artwork import AlbumArtSources
from stellody.domain.album import Album
from stellody.domain.searching import AlbumText, Found, Search, narrowed, prepared
from stellody.domain.track import Track
from stellody.ui.flashing import RowFlash
from stellody.ui.theme import palette_for


class Searching:
    """The narrowing half of the window."""

    def start_searching(self) -> None:
        """Begin holding the whole library, with nothing asked of it."""
        self._all_albums: tuple[Album, ...] = ()
        self._all_art: tuple[AlbumArtSources, ...] = ()
        self._prepared: tuple[AlbumText, ...] = ()
        self._search = Search()
        self._flash = RowFlash(self._model, self)

    def show_library(
        self, albums: tuple[Album, ...], art: tuple[AlbumArtSources, ...]
    ) -> None:
        """Take what a load or a scan produced, then show it as asked.

        Normalising the text is done here, once, rather than on every
        keystroke: measured, it is 9.2 milliseconds against 0.24 for the pass
        that uses it; the answer cannot change between keystrokes.
        """
        self._all_albums = albums
        self._all_art = art
        self._prepared = prepared(albums)
        self._narrow()

    def toggle_search(self) -> None:
        """Open the box, else close it, which restores the whole library.

        Closing clears the box, which reports an empty phrase like any other
        change, so nothing here has to undo the narrowing by hand.
        """
        self._tray.set_searching(not self._tray.searching)

    def search_changed(self, phrase: str) -> None:
        """Narrow to what has been typed so far."""
        self._search = Search(phrase=phrase)
        self._narrow()

    def _narrow(self) -> None:
        """Show the albums that survive, with the art that belongs to them.

        Whatever was open under the sleeves is put back afterwards, which
        cannot be done by leaving it alone: replacing every row leaves the
        pane rooted at an index that no longer means that album, so it
        re-roots on the whole library and lists it down BOTH columns. Keeping
        it open is done by opening it again.
        """
        found = narrowed(self._prepared, self._search)
        albums = tuple(one.album for one in found)
        keys = {album.identity.art_key for album in albums}
        was_open = self.pane_state()
        self._model.set_albums(albums)
        self.show_art(tuple(one for one in self._all_art if one.key in keys))
        if not self._point_at(found):
            self.restore_pane(was_open)

    def _point_at(self, found: tuple[Found, ...]) -> bool:
        """Select and flash the first track the phrase hit; True when it did.

        The first rather than all of them: a flash is a place to look;
        several at once is a page of flashing rather than a pointer. A phrase
        that hit nothing leaves whatever was open where it was.
        """
        self._flash.stop()
        for one in found:
            if one.tracks:
                self._show_track(one.tracks[0])
                return True
        return False

    def _show_track(self, track: Track) -> None:
        """Open whichever view is showing, put the highlight on the track,
        then flash its row."""
        where = self._model.index_for(track)
        if not where.isValid():
            return
        if self.showing_covers:
            self._open_sleeve(where)
        else:
            self._tree.setCurrentIndex(where)
            # Scrolling to the row is what opens every level above it, which a
            # multi-disc album needs since its tracks sit under a disc.
            # Measured: scrolling alone leaves both the disc and the album
            # open, where expanding the parent alone leaves the album shut.
            self._tree.scrollTo(where)
        self._flash.start(where, palette_for(self.theme_mode).found)

    def _open_sleeve(self, where: QModelIndex) -> None:
        """Open the album under the grid, with the highlight on the track.

        Picking the sleeve is what opens the pane; opening it leaves the
        highlight on the album's first track, so the track that was actually
        hit is chosen afterwards rather than before.
        """
        album = where
        while album.parent().isValid():
            album = album.parent()
        self._grid.setCurrentIndex(album)
        self._album_pane.columns[0].setCurrentIndex(where)
