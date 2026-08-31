"""How the library is shown: as a list, else as a grid of sleeves.

Both views are the same model, so neither can disagree with the other about
what the library holds or the order it is in. Switching between them keeps
that order, because there is only one of it.

Picking a sleeve opens the album underneath the grid rather than replacing
the grid, so the sleeves a listener was looking through stay where they were.
Pressing that sleeve again rolls the pane back up, which is the gesture that
opened it asked to undo itself. The pane's own close button does the same.
"""

from __future__ import annotations

from PySide6.QtCore import QEvent, QModelIndex, QObject, Qt, Slot
from PySide6.QtWidgets import QListView, QWidget

from stellody.domain.album import Album
from stellody.domain.track import Track
from stellody.ui.album_pane import AlbumPane
from stellody.ui.covering import DEFAULT_COVER_SIZE, CoverSize, next_cover_size
from stellody.ui.settings_keys import (
    FALSE,
    SETTING_COVER_SIZE,
    SETTING_COVERS,
    SETTING_DESCENDING,
    TRUE,
)
from stellody.ui.tiles import NO_ROW
from stellody.ui.window_parts import (
    build_covers_page,
    build_grid,
    build_library,
    fit_grid,
)

DECORATION = Qt.ItemDataRole.DecorationRole


class SleeveToggle(QObject):
    """Turns a second press on the open sleeve into a request to shut it.

    Read at the PRESS rather than at the click, because Qt moves the current
    index during the press: by the time `clicked` arrives, a first press on a
    fresh sleeve and a second press on the open one look alike. Pressing at all
    is also what makes a sleeve whose pane was closed open again, since it is
    still the current one and a selection that does not change says nothing.
    """

    def __init__(self, grid: QListView, viewing) -> None:
        super().__init__(grid)
        self._grid = grid
        self._viewing = viewing
        grid.viewport().installEventFilter(self)

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        """Shut the pane on a second press; open it on any other."""
        if event.type() is not QEvent.Type.MouseButtonPress:
            return False
        where = self._grid.indexAt(event.position().toPoint())
        if not where.isValid():
            return False
        if where == self._viewing.shown_index:
            self._viewing.close_album()
            # Eaten, so the sleeve stays the current one with its pane shut.
            # Qt would otherwise leave the selection exactly as it was anyway;
            # saying so here is what stops the press reopening what it closed.
            return True
        self._viewing.open_album_at(where)
        return False


class Viewing:
    """The window's half of choosing how the library is shown."""

    def start_viewing(self) -> QWidget:
        """Build the grid and its pane, then give back the holder to place."""
        self._grid = build_grid(self, self._model)
        self._tiles = self._grid.itemDelegate()
        self._album_pane = AlbumPane(self._model, self)
        self._album_pane.setVisible(False)
        self._album_pane.closed.connect(self.close_album)
        self._album_pane.play_wanted.connect(self.play_shown_album)
        self._album_pane.track_activated.connect(self.activate)
        self._album_pane.rated.connect(self.rate_album)
        self._album_pane.columns[0].selectionModel().currentChanged.connect(
            self._on_selection
        )
        # The same menu the list carries: a sleeve and a track in the open
        # album are the same gesture on the same library.
        self.wire_transport_menu(self._grid)
        for column in self._album_pane.columns:
            self.wire_transport_menu(column)
        self._grid.selectionModel().currentChanged.connect(self._on_album_picked)
        self._sleeve_toggle = SleeveToggle(self._grid, self)
        self._shown_album = None
        self._shown_index = QModelIndex()
        self._cover_size = DEFAULT_COVER_SIZE
        self._library = build_library(
            self, self._tree, build_covers_page(self, self._grid, self._album_pane)
        )
        return self._library

    @property
    def showing_covers(self) -> bool:
        """True while the grid of sleeves is the view on show."""
        return self._library.currentWidget() is not self._tree

    @Slot()
    def toggle_view(self) -> None:
        """Swap between the list and the sleeves, from the bottom strip."""
        self.show_covers(not self.showing_covers)

    def show_covers(self, covers: bool) -> None:
        """Show one view or the other, then remember which."""
        self._library.setCurrentIndex(1 if covers else 0)
        self._bottom_tray.set_showing_covers(covers)
        self._settings.set_setting(SETTING_COVERS, TRUE if covers else FALSE)
        if not covers:
            self.close_album()

    def restore_view(self) -> None:
        """Start in the view last chosen, the list when none has been."""
        self.restore_cover_size()
        self.show_covers(self._flag(SETTING_COVERS))

    @Slot()
    def toggle_cover_size(self) -> None:
        """Step the sleeves to the next size up, round to the smallest."""
        self.show_cover_size_choice(next_cover_size(self._cover_size))

    def restore_cover_size(self) -> None:
        """Start at the size last chosen, the middle one when none has been.

        A stored value that is not one of the sizes on offer falls back to the
        default rather than to whatever it says, since a grid drawn at a number
        nobody chose is worse than a grid drawn at the size a first run uses.
        """
        stored = self._settings.get_setting(SETTING_COVER_SIZE, "")
        try:
            size = CoverSize(int(stored))
        except ValueError:
            size = DEFAULT_COVER_SIZE
        self.show_cover_size_choice(size)

    def show_cover_size_choice(self, size: CoverSize) -> None:
        """Draw the sleeves at this size, show what is next and remember it."""
        self._cover_size = size
        self._tiles.show_cover_size(size)
        fit_grid(self._grid)
        self.show_cover_size(size)
        self._bottom_tray.set_next_cover_size(next_cover_size(size))
        self._settings.set_setting(SETTING_COVER_SIZE, str(int(size)))

    @property
    def shown_index(self) -> QModelIndex:
        """Where the open album sits; an invalid index while none is open."""
        return self._shown_index

    @Slot()
    def close_album(self) -> None:
        """Shut the pane. The grid keeps the place it was scrolled to."""
        self._shown_album = None
        self._shown_index = QModelIndex()
        self._album_pane.setVisible(False)
        self._album_pane.clear()
        self._ring_open(NO_ROW)

    @Slot()
    def play_shown_album(self) -> None:
        """Play the open album from its first track."""
        album = self._shown_album
        if album is None:
            return
        self.play_album(album)

    @Slot(QModelIndex, QModelIndex)
    def _on_album_picked(self, current: QModelIndex, _previous: QModelIndex) -> None:
        """Open the picked album under the grid; shut the pane when none is."""
        self.open_album_at(current)

    def open_album_at(self, where: QModelIndex) -> None:
        """Show this album under the grid, unless it is the one already on.

        Reopening the album already open would put the highlight back on its
        first track, undoing whatever the listener had chosen since; a press
        and the selection change it causes both arrive, so this is asked twice
        for one gesture.
        """
        if where == self._shown_index and self._shown_album is not None:
            return
        album = self._model.album_at(where)
        if album is None:
            self.close_album()
            return
        self._shown_album = album
        self._shown_index = where
        self._album_pane.show_album(album, where, self._model.data(where, DECORATION))
        self.show_album_rating()
        self._album_pane.setVisible(True)
        self._ring_open(where.row())

    def show_pane_cover(self, key: str) -> None:
        """Put a sleeve on the open album once it has actually been read.

        The pane takes its sleeve as it opens, which a search does before any
        cover can have arrived. Ignored for every album but the open one, so a
        library reading its way down the grid does not repaint the pane.
        """
        album = self._shown_album
        if album is None or album.identity.art_key != key:
            return
        self._album_pane.show_cover(self._model.cover_for(key))

    def pane_state(self) -> tuple[Album, Track | None] | None:
        """The album the pane is showing and the track chosen in it."""
        album = self._shown_album
        if album is None:
            return None
        return album, self._model.track_at(self._album_pane.current_index())

    def restore_pane(self, was_open: tuple[Album, Track | None] | None) -> None:
        """Put the pane back on the album it held, with the track it held.

        It shuts only where that album is no longer among the sleeves, since
        there is then no row anywhere to root it at.
        """
        if was_open is None:
            return
        album, track = was_open
        where = self._album_index(album)
        if not where.isValid():
            self.close_album()
            return
        # Shut first, because opening the album it believes is already open
        # does nothing; what it believes is a row that has been replaced.
        self.close_album()
        self.open_album_at(where)
        if track is None:
            return
        # A rescan builds every track afresh as well, so the one that was
        # chosen may not be findable even though its album is. Opening the
        # album has already left the highlight on its first track, which is
        # better than clearing it to nothing.
        at = self._model.index_for(track)
        if at.isValid():
            self._album_pane.columns[0].setCurrentIndex(at)

    def _album_index(self, album: Album) -> QModelIndex:
        """Where this album sits now; an invalid index when it is not shown.

        By the album's identity rather than by the object, because a rescan
        builds every album afresh: the same album comes back as a different
        object and the pane would shut for no reason a listener could see.
        """
        wanted = album.identity.key
        for row in range(self._model.rowCount(QModelIndex())):
            where = self._model.index(row, 0, QModelIndex())
            found = self._model.album_at(where)
            if found is not None and found.identity.key == wanted:
                return where
        return QModelIndex()

    def show_tile_appearance(self, mode) -> None:
        """Draw the sleeves in the appearance the window is wearing."""
        self._tiles.show_appearance(mode)
        self._album_pane.show_appearance(mode)
        self._grid.viewport().update()

    def _ring_open(self, row: int) -> None:
        """Say which sleeve is the one showing underneath, then redraw."""
        self._tiles.show_open(row)
        self._grid.viewport().update()

    @Slot()
    def toggle_order(self) -> None:
        """Invert the album order and remember it."""
        descending = not self._model.descending
        was_open = self.pane_state()
        self._model.set_descending(descending)
        self.restore_pane(was_open)
        self._descending_action.setChecked(descending)
        self._settings.set_setting(SETTING_DESCENDING, TRUE if descending else FALSE)
