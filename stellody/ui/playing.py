"""Driving the transport from the window, then showing what it is doing.

Split from the window for the same reason the scanning is: over there is what
the window IS, here is what the buttons under it do. Everything with an opinion
about queues and devices lives in the application layer; this only presses.

The device is asked what it is doing rather than telling anyone. A track
reaching its end raises no event, so a timer asks, which is the same timer that
keeps the play button showing the right face.
"""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QModelIndex, QPoint, Qt, Slot
from PySide6.QtWidgets import QMenu

from stellody.ui.settings_keys import STATUS_TIMEOUT_MS

# Often enough that the button never lies for long, rarely enough that an idle
# window is not doing arithmetic sixty times a second.
TRANSPORT_POLL_MS = 250


class Playing:
    """The transport half of the window."""

    def wire_tree(self) -> None:
        """Give the library the two ways of starting a track, plus its menu.

        Measured on this tree: one double click emits BOTH `doubleClicked` and
        `activated`; Return emits `activated` alone. So `activated` covers
        both gestures and is the only one connected. Connecting the pair loads
        the track twice for one double click, which restarts it audibly.

        Measured again in isolation, a bare QTreeView emitted `doubleClicked`
        only, which is why this says which tree it was measured on.
        """
        self._tree.activated.connect(self.activate)
        self._tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._tree.customContextMenuRequested.connect(self.show_transport_menu)

    @Slot(QPoint)
    def show_transport_menu(self, where: QPoint) -> None:
        """Offer the transport over whatever was right clicked.

        Play means the track under the cursor when there is one, since that is
        what right clicking a track is asking about; over anything else it
        resumes what is loaded.
        """
        index = self._tree.indexAt(where)
        track = self._model.track_at(index)
        menu = QMenu(self._tree)
        playing = self._transport.playing
        loaded = self._transport.current is not None
        play = menu.addAction("Play")
        play.setEnabled(track is not None or (loaded and not playing))
        play.triggered.connect(
            (lambda: self.activate(index))
            if track is not None
            else self.toggle_playback
        )
        pause = menu.addAction("Pause")
        pause.setEnabled(playing)
        pause.triggered.connect(self.toggle_playback)
        stop = menu.addAction("Stop")
        stop.setEnabled(self._transport.state.is_active)
        stop.triggered.connect(self.stop_playback)
        menu.addSeparator()
        previous = menu.addAction("Previous track")
        previous.setEnabled(self._transport.queue.has_previous)
        previous.triggered.connect(self.previous_track)
        following = menu.addAction("Next track")
        following.setEnabled(self._transport.queue.has_next)
        following.triggered.connect(self.next_track)
        self._menu = menu
        menu.popup(self._tree.viewport().mapToGlobal(where))

    @Slot(QModelIndex)
    def activate(self, index: QModelIndex) -> None:
        """Play the track that was double clicked or opened with Return.

        Activating an album is left to the tree, which expands it: an album is
        a container, so opening it means showing what is inside.
        """
        track = self._model.track_at(index)
        if track is None:
            return
        album = self._model.album_at(index)
        if album is None:
            return
        if self._drive(lambda: self._transport.play_album(album, track)):
            self.statusBar().showMessage(f"Playing {track.title}", STATUS_TIMEOUT_MS)

    @Slot()
    def toggle_playback(self) -> None:
        """Pause what is playing, resume what is not."""
        self._drive(self._transport.toggle)

    @Slot()
    def stop_playback(self) -> None:
        """End playback and give the device back."""
        self._drive(self._transport.stop)

    @Slot()
    def previous_track(self) -> None:
        """Play the track before this one."""
        self._drive(self._transport.previous)

    @Slot()
    def next_track(self) -> None:
        """Play the track after this one."""
        self._drive(self._transport.next)

    @Slot()
    def _poll_transport(self) -> None:
        """Move on at the end of a track; keep the buttons honest."""
        self._drive(self._transport.advance_if_finished)

    def _drive(self, action: Callable[[], object]) -> bool:
        """Run one transport command, saying so when it cannot be done.

        Opening a device is the one thing here that can fail: a file that will
        not decode, a device another application holds exclusively, a drive
        unplugged since the library was scanned. Every one of those raises out
        of the port; an exception raised inside a Qt slot ends the slot in
        silence: the buttons would keep their faces and nothing would play,
        with nothing said. So it is caught here and reported.
        """
        try:
            action()
        except (OSError, RuntimeError, ValueError) as error:
            self._transport.stop()
            self._show_transport()
            self.statusBar().showMessage(f"Cannot play that: {error}")
            return False
        self._show_transport()
        return True

    def _show_transport(self) -> None:
        """Point the buttons at what can be done to what is loaded."""
        playing = self._transport.playing
        self._tray.set_playing(playing)
        self._tray.set_transport_enabled(
            loaded=self._transport.current is not None,
            playing=self._transport.state.is_active,
        )
