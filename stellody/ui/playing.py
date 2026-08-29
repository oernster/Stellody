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

from stellody.ui.bottom_tray import MAXIMUM_PERCENT, MINIMUM_PERCENT
from stellody.ui.settings_keys import (
    FALSE,
    SETTING_MUTED,
    SETTING_REPEAT,
    SETTING_SHUFFLE,
    SETTING_VOLUME,
    STATUS_TIMEOUT_MS,
    TRUE,
)

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

    @Slot(int)
    def set_volume(self, percent: int) -> None:
        """Take the slider's whole percent down to the gain the engine wants.

        Stored as percent because that is what the user set and what the
        tooltip says; the fraction is the engine's business and the conversion
        happens once, here.
        """
        self._transport.set_volume(percent / MAXIMUM_PERCENT)
        self._bottom_tray.set_percent(percent)
        self._settings.set_setting(SETTING_VOLUME, str(percent))

    def restore_volume(self) -> None:
        """Start at the volume last chosen, full when none has been."""
        stored = self._settings.get_setting(SETTING_VOLUME, str(MAXIMUM_PERCENT))
        try:
            percent = int(stored)
        except ValueError:
            percent = MAXIMUM_PERCENT
        self.set_volume(min(max(MINIMUM_PERCENT, percent), MAXIMUM_PERCENT))

    def restore_switches(self) -> None:
        """Bring mute, shuffle and repeat back as they were last left.

        A switch that forgets itself between sessions is a switch the listener
        has to set every time, which is the same as not having it.
        """
        self._apply_muted(self._flag(SETTING_MUTED))
        self._apply_shuffled(self._flag(SETTING_SHUFFLE))
        self._apply_repeating(self._flag(SETTING_REPEAT))

    def toggle_mute(self) -> None:
        """Silence the output, else give it back at the level already chosen."""
        self._apply_muted(not self._transport.muted)

    def toggle_shuffle(self) -> None:
        """Scatter the queue, else put the album back into its own order."""
        self._apply_shuffled(not self._transport.shuffled)

    def toggle_repeat(self) -> None:
        """Choose between the queue ending at its last track and looping."""
        self._apply_repeating(not self._transport.repeating)

    def _apply_muted(self, muted: bool) -> None:
        """Set the switch, show it and remember it: the three go together."""
        self._transport.set_muted(muted)
        self._tray.set_muted(muted)
        self._remember(SETTING_MUTED, muted)

    def _apply_shuffled(self, shuffled: bool) -> None:
        """Set the switch, show it and remember it."""
        self._transport.set_shuffled(shuffled)
        self._bottom_tray.set_shuffled(shuffled)
        self._remember(SETTING_SHUFFLE, shuffled)

    def _apply_repeating(self, repeating: bool) -> None:
        """Set the switch, show it and remember it."""
        self._transport.set_repeating(repeating)
        self._bottom_tray.set_repeating(repeating)
        self._remember(SETTING_REPEAT, repeating)

    def _remember(self, key: str, on: bool) -> None:
        """Store one switch under the name it is read back by."""
        self._settings.set_setting(key, TRUE if on else FALSE)

    @Slot(QModelIndex, QModelIndex)
    def _on_selection(self, current: QModelIndex, previous: QModelIndex) -> None:
        """Selecting a track is what makes the play button pressable."""
        self._show_transport()

    @Slot(QPoint)
    def show_transport_menu(self, where: QPoint) -> None:
        """Offer the transport over whatever was right clicked.

        Play means the track under the cursor when that is a DIFFERENT track,
        since that is what right clicking another row is asking about. On the
        track already loaded it means carry on, exactly as it does over empty
        space: starting a track over is what next and previous are for;
        losing your place in a long piece is not a small annoyance.

        The distinction was not always this load bearing. The highlight now
        follows the transport, so the row under the cursor is usually the one
        being played, which is precisely the case that used to reload.
        """
        index = self._tree.indexAt(where)
        track = self._model.track_at(index)
        menu = QMenu(self._tree)
        playing = self._transport.playing
        loaded = self._transport.current is not None
        elsewhere = track is not None and track is not self._transport.current
        play = menu.addAction("Play")
        play.setEnabled(elsewhere or (loaded and not playing))
        play.triggered.connect(
            (lambda: self.activate(index)) if elsewhere else self.toggle_playback
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
        """Pause what is playing, resume what is not, start what is chosen.

        With an empty queue there is nothing to resume, so play means the track
        highlighted in the library. That is what somebody who selected a track
        and reached for the play button meant by it.
        """
        if self._transport.current is None:
            self.activate(self._tree.currentIndex())
            return
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
        self._follow_playback()
        self._show_transport()
        return True

    def _follow_playback(self) -> None:
        """Point the library at the track playing, whenever that changes.

        Only on a change. The transport is polled four times a second, so
        following on every poll would drag the highlight back from wherever
        the listener had moved it to while the music carried on.

        The parent is expanded first: a highlight on a row inside a collapsed
        album is a highlight nobody can see.
        """
        track = self._transport.current
        if track is None or track is self._followed:
            return
        self._followed = track
        index = self._model.index_for(track)
        if not index.isValid():
            return
        self._tree.expand(index.parent())
        self._tree.setCurrentIndex(index)
        self._tree.scrollTo(index)

    def _show_transport(self) -> None:
        """Point the buttons at what can be done to what is loaded."""
        playing = self._transport.playing
        self._tray.set_playing(playing)
        self._tray.set_transport_enabled(
            loaded=self._transport.current is not None,
            playing=self._transport.state.is_active,
            can_start=self._model.track_at(self._tree.currentIndex()) is not None,
        )
