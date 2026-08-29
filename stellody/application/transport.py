"""Playing a queue through whatever device is behind the playback port.

The window presses buttons; this decides what they mean. It owns the queue and
the one rule that ties the queue to the device: loading a track always leaves
it playing, because nothing else is what pressing next means.

No Qt, no device, no filesystem. The port is the only way out.
"""

from __future__ import annotations

from stellody.application.ports import PlaybackPort
from stellody.domain.album import Album
from stellody.domain.playback import OutputRequest, PlaybackState
from stellody.domain.queue import Queue, queue_from
from stellody.domain.track import Track


class Transport:
    """The transport the window drives: a queue, plus a device to play it on."""

    def __init__(self, player: PlaybackPort) -> None:
        self._player = player
        self._queue = Queue()

    @property
    def queue(self) -> Queue:
        """What is lined up, plus where in it playback has reached."""
        return self._queue

    @property
    def current(self) -> Track | None:
        """The track loaded, else the one that would be; None when idle."""
        return self._queue.current

    @property
    def state(self) -> PlaybackState:
        """Where the transport is, as the device reports it."""
        return self._player.state

    @property
    def playing(self) -> bool:
        """Whether sound is being produced right now."""
        return self._player.state is PlaybackState.PLAYING

    def play_album(self, album: Album, first: Track) -> None:
        """Queue an album and start at the track that was activated."""
        self._queue = queue_from(album.ordered_tracks(), first)
        self._load_current()

    def toggle(self) -> None:
        """Pause what is playing, resume what is not.

        With nothing loaded there is nothing to toggle. The queue is then what
        would be played rather than what is, so pressing play starts it.
        """
        if self._player.state is PlaybackState.PLAYING:
            self._player.pause()
            return
        if self._player.state is PlaybackState.PAUSED:
            self._player.play()
            return
        self._load_current()

    def stop(self) -> None:
        """Give the device back, keeping the queue where it is."""
        self._player.stop()

    def next(self) -> None:
        """Play the following track; nothing at the end of the queue."""
        moved = self._queue.next()
        if moved is self._queue:
            return
        self._queue = moved
        self._load_current()

    def previous(self) -> None:
        """Play the preceding track; nothing at the start of the queue."""
        moved = self._queue.previous()
        if moved is self._queue:
            return
        self._queue = moved
        self._load_current()

    def advance_if_finished(self) -> bool:
        """Move on when the track has played out; True when something changed.

        A track ending is not reported by the device, so it is asked about.
        The last track in a queue ends by stopping, rather than by looping or
        by leaving the device open on silence.
        """
        if not self._player.finished:
            return False
        if not self._queue.has_next:
            self._player.stop()
            return True
        self.next()
        return True

    def _load_current(self) -> None:
        """Open the current track and start it. Nothing to open is not a fault."""
        track = self._queue.current
        if track is None:
            return
        self._player.load(
            track.source,
            OutputRequest(sample_rate=track.sample_rate, bit_depth=track.bit_depth),
        )
        self._player.play()
