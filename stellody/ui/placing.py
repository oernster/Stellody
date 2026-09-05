"""Where the library was looking, kept across a reload that changes nothing
about where it should be looking.

Stating a genre replaces the whole library: the store is read again and every
album comes back as a new object, so the model is rebuilt from the top. That is
right for what the rows SAY and wrong for where somebody is: a listener who
scrolled two thirds of the way down to correct one album should still be two
thirds of the way down when it is corrected.

**A place is not a row number.** The library after an edit is not the library
before it: albums fold together, an edit to an artist moves one somewhere else
alphabetically. So a place names the album by identity and the offset in
pixels; the row is worked out again on the other side.

**Where possible; no further.** An album that is gone after the edit takes
its own restoring with it; the offset still goes back, since a listener looking
at the middle of the library is still looking at the middle of it. Nothing here
scrolls to something that was not on screen to begin with.
"""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import QModelIndex

from stellody.domain.album import Album
from stellody.domain.track import Track


@dataclass(frozen=True, slots=True)
class Place:
    """Where the library was: what was open, what was current, how far down."""

    # The pane's album and the track chosen in it, as `pane_state` gives them.
    open_album: tuple[Album, Track | None] | None
    # The album the keyboard was on, by identity, whether or not it was open.
    current_key: str
    # How far down the sleeves were, in pixels.
    offset: int


class KeepingPlace:
    """The window's half of staying where it was across a reload."""

    def start_keeping_place(self) -> None:
        """Begin with nothing being restored."""
        # True only while a place is being put back. What it stops is the
        # highlight reopening the pane: the pane is restored first and by
        # name, so a current index arriving afterwards would open an album
        # over the top of the one that was already put back.
        self._holding_place = False

    def library_place(self) -> Place:
        """Where the library is looking now."""
        current = self._grid.currentIndex()
        album = self._model.album_at(current) if current.isValid() else None
        return Place(
            open_album=self.pane_state(),
            current_key=album.identity.key if album is not None else "",
            offset=self._grid.verticalScrollBar().value(),
        )

    def restore_place(self, place: Place) -> None:
        """Put the library back where it was, as far as it still exists.

        In this order for a reason: the pane first, because it decides what
        the grid is asked to show; the highlight next, held back from opening
        anything; the offset last, since both of the others can scroll.
        """
        self._holding_place = True
        try:
            self.restore_pane(place.open_album)
            self._put_the_highlight_back(place.current_key)
        finally:
            self._holding_place = False
        self._grid.glide.stop()
        self._grid.verticalScrollBar().setValue(place.offset)

    def _put_the_highlight_back(self, key: str) -> None:
        """Make the album with that identity current again, where it is still
        there. An empty key means nothing was current, which is left alone."""
        if not key:
            return
        where: QModelIndex = self.index_of_key(key)
        if where.isValid():
            self._grid.setCurrentIndex(where)
