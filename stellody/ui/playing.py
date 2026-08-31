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

from PySide6.QtCore import QModelIndex, Slot

from stellody.ui.settings_keys import (
    FALSE,
    SETTING_MUTED,
    SETTING_REPEAT,
    SETTING_SHUFFLE,
    SETTING_VOLUME,
    STATUS_TIMEOUT_MS,
    TRUE,
)
from stellody.ui.volume import DEFAULT_PERCENT, MAXIMUM_PERCENT, MINIMUM_PERCENT

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
        self.wire_transport_menu(self._tree)

    @Slot(int)
    def set_volume(self, percent: int) -> None:
        """Take the slider's whole percent down to the gain the engine wants.

        Stored as percent because that is what the user set and what the
        tooltip says; the fraction is the engine's business and the conversion
        happens once, here.
        """
        self._transport.set_volume(percent / MAXIMUM_PERCENT)
        self._tray.set_percent(percent)
        self._settings.set_setting(SETTING_VOLUME, str(percent))

    def restore_volume(self) -> None:
        """Start at the volume last chosen, at the default when none has been.

        A stored value that cannot be read as a number falls back to the same
        default rather than to silence or to full: both of those are a worse
        surprise than the level a first run would have used.
        """
        stored = self._settings.get_setting(SETTING_VOLUME, str(DEFAULT_PERCENT))
        try:
            percent = int(stored)
        except ValueError:
            percent = DEFAULT_PERCENT
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
        """Selecting a track is what makes the play button pressable.

        The bar is told at once rather than at the next poll, so a shape
        appears as the highlight lands on a track instead of a beat later.
        """
        self._show_transport()
        self.follow_shape()
        self.follow_rating()

    def play_album(self, album) -> None:
        """Start an album from its first track."""
        ordered = album.ordered_tracks()
        if not ordered:
            return
        self._drive(lambda: self._transport.play_album(album, ordered[0]))

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

        Highlighted in the view ON SHOW, which is the open album while the
        sleeves are up. Reading the list either way left the button dead in
        the grid, where the list is not the thing being looked at.

        A loaded track used to make this a resume WHATEVER had been chosen
        since, so picking a second album and pressing play started the first
        one again. Play now means the highlighted track wherever that is not
        the track already loaded, which is the rule the right click menu has
        always followed.

        While something is PLAYING the button is a pause button, so it pauses
        even with another album picked: a press on a pause button is asking to
        stop rather than to go somewhere else. The press after it starts what
        was picked.
        """
        chosen = self._model.track_at(self.highlighted())
        elsewhere = chosen is not None and chosen is not self._transport.current
        if self._transport.current is None or (
            elsewhere and not self._transport.playing
        ):
            self.activate(self.highlighted())
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
        """Move on at the end of a track; keep the buttons and the bar honest."""
        self._drive(self._transport.advance_if_finished)
        self._position_bar.show_position(self._transport.position)
        self.follow_shape()
        self.follow_rating()

    @Slot(int)
    def seek_to(self, frame: int) -> None:
        """Move within the track in hand, in the listener's own frames."""
        self._drive(lambda: self._transport.seek(frame))
        self._position_bar.show_position(self._transport.position)

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

        What is remembered as followed is what the tree is actually showing,
        set once the highlight has moved rather than before. Setting it first
        meant a placement that did not happen was remembered as one that had:
        the highlight then stayed on the track that had just ended and every
        later poll agreed there was nothing to do.

        The listener is still left alone. Where they have moved the highlight
        themselves and the same track is still playing, it stays where they
        put it: the transport is polled four times a second and dragging it
        back would make browsing during playback impossible.

        The parent is expanded first: a highlight on a row inside a collapsed
        album is a highlight nobody can see.
        """
        track = self._transport.current
        if track is None:
            return
        showing = self._model.track_at(self._tree.currentIndex())
        if showing is track:
            self._followed = track
            return
        if track is self._followed and showing is not self._followed:
            return
        index = self._model.index_for(track)
        if not index.isValid():
            return
        self._tree.expand(index.parent())
        self._tree.setCurrentIndex(index)
        self._tree.scrollTo(index)
        self._followed = track

    def highlighted(self) -> QModelIndex:
        """The row the play button would start, in the view now on show."""
        if self.showing_covers:
            return self._album_pane.current_index()
        return self._tree.currentIndex()

    def _show_transport(self) -> None:
        """Point the buttons at what can be done to what is loaded."""
        playing = self._transport.playing
        self._tray.set_playing(playing)
        self._album_pane.set_playing(playing)
        self._tray.set_transport_enabled(
            loaded=self._transport.current is not None,
            playing=self._transport.state.is_active,
            can_start=self._model.track_at(self.highlighted()) is not None,
        )
        self._position_bar.show_position(self._transport.position)
