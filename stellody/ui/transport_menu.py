"""The menu offered over a right click, wherever the right click landed.

Split out of the transport half, which had grown past the length a module is
allowed here. The split is along a real seam rather than an arbitrary one: over
there is what the buttons DO, here is the one surface that asks what a listener
meant by pointing at something.

The same menu serves the list, the grid of sleeves and the open album, because
all three are the same library and pointing at a row of it is the same gesture.
The view is passed in rather than assumed, since the signal carries a point and
nothing else.
"""

from __future__ import annotations

from PySide6.QtCore import QPoint, Qt
from PySide6.QtWidgets import QAbstractItemView, QMenu


class TransportMenu:
    """The window's half of answering a right click over the library."""

    def wire_transport_menu(self, over: QAbstractItemView) -> None:
        """Offer the transport over this view, whichever view it is."""
        over.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        over.customContextMenuRequested.connect(
            lambda where, view=over: self.show_transport_menu(where, view)
        )

    def show_transport_menu(self, where: QPoint, over=None) -> None:
        """Offer the transport over whatever was right clicked.

        Play means the track under the cursor when that is a DIFFERENT track,
        since that is what right clicking another row is asking about. On the
        track already loaded it means carry on, exactly as it does over empty
        space: starting a track over is what next and previous are for;
        losing your place in a long piece is not a small annoyance.

        The distinction was not always this load bearing. The highlight now
        follows the transport, so the row under the cursor is usually the one
        being played, which is precisely the case that used to reload.

        A sleeve carries no track of its own, so Play over one means the album
        from its first track. Over the album already loaded it means carry on,
        for exactly the reason a loaded track does.
        """
        over = self._tree if over is None else over
        index = over.indexAt(where)
        track = self._model.track_at(index)
        album = self._model.album_at(index)
        menu = QMenu(over)
        playing = self._transport.playing
        loaded = self._transport.current is not None
        elsewhere = track is not None and track is not self._transport.current
        starts = track is None and album is not None and self._album_elsewhere(album)
        play = menu.addAction("Play")
        play.setEnabled(elsewhere or starts or (loaded and not playing))
        if elsewhere:
            play.triggered.connect(lambda: self.activate(index))
        elif starts:
            play.triggered.connect(lambda: self.play_album(album))
        else:
            play.triggered.connect(self.toggle_playback)
        pause = menu.addAction("Pause")
        pause.setEnabled(playing)
        pause.triggered.connect(self.toggle_playback)
        stop = menu.addAction("Stop")
        stop.setEnabled(self._transport.state.is_active)
        stop.triggered.connect(self.stop_playback)
        menu.addSeparator()
        previous = menu.addAction("Previous track")
        # Offered wherever the button is, because back on the first track
        # starts it again rather than doing nothing.
        previous.setEnabled(self._transport.current is not None)
        previous.triggered.connect(self.previous_track)
        following = menu.addAction("Next track")
        following.setEnabled(self._transport.queue.has_next)
        following.triggered.connect(self.next_track)
        self._menu = menu
        menu.popup(over.viewport().mapToGlobal(where))

    def _album_elsewhere(self, album) -> bool:
        """True while this album is not the one already loaded.

        By identity rather than equality, matching the queue: two pressings can
        compare equal while only one of them is the run that is playing.
        """
        current = self._transport.current
        return current is None or not any(
            candidate is current for candidate in album.ordered_tracks()
        )
