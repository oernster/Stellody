"""How the library is shown: as a list, else as a grid of sleeves.

Both views are the same model, so neither can disagree with the other about
what the library holds or the order it is in. Switching between them keeps
that order, because there is only one of it.

Picking a sleeve opens the album underneath the grid rather than replacing
the grid, so the sleeves a listener was looking through stay where they were.
"""

from __future__ import annotations

from PySide6.QtCore import QModelIndex, Qt, Slot
from PySide6.QtWidgets import QWidget

from stellody.ui.album_pane import AlbumPane
from stellody.ui.settings_keys import FALSE, SETTING_COVERS, SETTING_DESCENDING, TRUE
from stellody.ui.window_parts import build_covers_page, build_grid, build_library

DECORATION = Qt.ItemDataRole.DecorationRole


class Viewing:
    """The window's half of choosing how the library is shown."""

    def start_viewing(self) -> QWidget:
        """Build the grid and its pane, then give back the holder to place."""
        self._grid = build_grid(self, self._model)
        self._album_pane = AlbumPane(self._model, self)
        self._album_pane.setVisible(False)
        self._album_pane.closed.connect(self.close_album)
        self._album_pane.play_wanted.connect(self.play_shown_album)
        self._album_pane.tracks.activated.connect(self.activate)
        self._grid.selectionModel().currentChanged.connect(self._on_album_picked)
        self._shown_album = None
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
        self.show_covers(self._flag(SETTING_COVERS))

    @Slot()
    def close_album(self) -> None:
        """Shut the pane. The grid keeps the place it was scrolled to."""
        self._shown_album = None
        self._album_pane.setVisible(False)
        self._album_pane.tracks.setRootIndex(QModelIndex())

    @Slot()
    def play_shown_album(self) -> None:
        """Play the open album from its first track."""
        album = self._shown_album
        if album is None:
            return
        ordered = album.ordered_tracks()
        if not ordered:
            return
        self._drive(lambda: self._transport.play_album(album, ordered[0]))

    @Slot(QModelIndex, QModelIndex)
    def _on_album_picked(self, current: QModelIndex, _previous: QModelIndex) -> None:
        """Open the picked album under the grid; shut the pane when none is."""
        album = self._model.album_at(current)
        if album is None:
            self.close_album()
            return
        self._shown_album = album
        self._album_pane.show_album(
            album, current, self._model.data(current, DECORATION)
        )
        self._album_pane.setVisible(True)

    @Slot()
    def toggle_order(self) -> None:
        """Invert the album order and remember it."""
        descending = not self._model.descending
        self._model.set_descending(descending)
        self._descending_action.setChecked(descending)
        self._settings.set_setting(SETTING_DESCENDING, TRUE if descending else FALSE)
