"""Driving the transport from the window, then showing what it is doing.

Split from the window for the same reason the scanning is: over there is what
the window IS, here is what the buttons under it do. Everything with an opinion
about queues and devices lives in the application layer; this only presses.

The device is asked what it is doing rather than telling anyone. A track
reaching its end raises no event, so a timer asks, which is the same timer that
keeps the play button showing the right face.

The switches (volume, mute, shuffle, repeat, the equaliser) are in
`switches.py`; saying what is playing is `now_playing.py`'s.
"""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QModelIndex, Slot

from stellody.ui.settings_keys import UNPLAYABLE_MESSAGE_MS

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
        """Play the track that was opened; pause the one already loaded.

        Opening the track ALREADY LOADED means play or pause rather than start
        again, which is Oliver's ruling and is what the transport button and
        the right click menu have always done with it. Starting it over is
        what a listener asking to pause got instead, since the row under the
        keyboard is the playing row.

        One rule for the keyboard and for the mouse, since this is the one
        place both gestures arrive: a double click on the playing track pauses
        it too rather than the two meaning different things on one row.

        Activating an album is left to the tree, which expands it: an album is
        a container, so opening it means showing what is inside.

        Nothing is said here about what started. A message written only by
        this gesture went on naming the old track after Next and after a
        play-out, so the foot is written from the transport on every change
        instead. See `now_playing.py`.
        """
        track = self._model.track_at(index)
        if track is None:
            return
        if track is self._transport.current:
            self._drive(self._transport.toggle)
            return
        album = self._model.album_at(index)
        if album is None:
            return
        self._drive(lambda: self._transport.play_album(album, track))

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
        self.follow_picture()

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

        Here is the only place it can be caught. The transport used to catch
        it and report through a callback instead, which left this returning
        True on a failure: the device was never given back and the caller went
        on to say the track was playing, over the top of the message saying it
        would not. The track is named from the transport because the one that
        failed is not always the one somebody pressed; a track running out
        into an unreadable next one arrives here through the poll.
        """
        try:
            action()
        except (OSError, RuntimeError, ValueError) as error:
            failed = self._transport.current
            self._transport.stop()
            self._show_transport()
            named = "Cannot play that"
            if failed is not None:
                named = f"{failed.title} could not be played"
            self.statusBar().showMessage(f"{named}: {error}", UNPLAYABLE_MESSAGE_MS)
            return False
        self._follow_playback()
        self._show_transport()
        return True

    def _follow_playback(self) -> None:
        """Point the library at the track playing, whenever that changes.

        What is remembered as followed is what the view is actually showing,
        set once the highlight has moved rather than before. Setting it first
        meant a placement that did not happen was remembered as one that had:
        the highlight then stayed on the track that had just ended and every
        later poll agreed there was nothing to do.

        The listener is still left alone. Where they have moved the highlight
        themselves and the same track is still playing, it stays where they
        put it: the transport is polled four times a second and dragging it
        back would make browsing during playback impossible.

        Which highlight moves depends on the view now on show, which is
        why both halves of this go through `highlighted` and
        `_show_highlight` rather than through the tree. The grid keeps its
        own highlight in the album open under it, so pointing the tree at a
        track left the visible one where it was: reported against an album
        playing through, where nothing on screen said what was playing.
        """
        track = self._transport.current
        if track is None:
            return
        showing = self._model.track_at(self.highlighted())
        if showing is track:
            self._followed = track
            return
        if track is self._followed and showing is not self._followed:
            return
        index = self._model.index_for(track)
        if not index.isValid():
            return
        if not self._show_highlight(index):
            return
        self._followed = track

    def _show_highlight(self, index: QModelIndex) -> bool:
        """Move the highlight in the view on show; False if it could not.

        In the tree, `scrollTo` opens every level above the row, which a
        multi-disc album needs since its tracks sit under a disc: a
        highlight inside a collapsed album is one nobody can see. The pane
        refuses a track of an album it is not showing, which is what keeps
        the answer honest rather than merely quiet.
        """
        if self.showing_covers:
            return self._album_pane.show_track(index)
        self._tree.expand(index.parent())
        self._tree.setCurrentIndex(index)
        self._tree.scrollTo(index)
        return True

    def highlighted(self) -> QModelIndex:
        """The row the play button would start, in the view now on show."""
        if self.showing_covers:
            return self._album_pane.current_index()
        return self._tree.currentIndex()

    def _show_transport(self) -> None:
        """Point the buttons at what can be done to what is loaded.

        The mark and the name go from here too, since this is reached after
        every command, after a failure and after every poll: one place means
        no path that changes the track can leave either behind.
        """
        playing = self._transport.playing
        self._tray.set_playing(playing)
        self._album_pane.set_playing(playing)
        self._tray.set_transport_enabled(
            loaded=self._transport.current is not None,
            playing=self._transport.state.is_active,
            can_start=self._model.track_at(self.highlighted()) is not None,
        )
        self._position_bar.show_position(self._transport.position)
        self.follow_spectrum()
        self.show_now_playing()
