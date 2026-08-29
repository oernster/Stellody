"""Playing a queue through whatever device is behind the playback port.

The window presses buttons; this decides what they mean. It owns the queue and
the one rule that ties the queue to the device: loading a track always leaves
it playing, because nothing else is what pressing next means.

No Qt, no device, no filesystem. The port is the only way out.
"""

from __future__ import annotations

import random
import time
from collections.abc import Callable

from stellody.application.ports import PlaybackPort
from stellody.domain.album import Album
from stellody.domain.playback import (
    SILENT_VOLUME,
    UNITY_VOLUME,
    OutputRequest,
    PlaybackState,
)
from stellody.domain.queue import Queue, queue_from
from stellody.domain.track import MILLISECONDS_PER_SECOND, Track

Ordering = Callable[[tuple[Track, ...]], tuple[Track, ...]]

Clock = Callable[[], float]

# How close two presses of back must fall for the second to mean the previous
# track. Longer than a double click, because this is a decision rather than a
# gesture; short enough that a press made minutes later is plainly a fresh one.
QUICK_PRESS_MS = 2000


def scattered(tracks: tuple[Track, ...]) -> tuple[Track, ...]:
    """These tracks in an arbitrary order. The default way shuffle shuffles."""
    return tuple(random.sample(tracks, len(tracks)))


class Transport:
    """The transport the window drives: a queue, plus a device to play it on."""

    def __init__(
        self,
        player: PlaybackPort,
        ordering: Ordering = scattered,
        now: Clock = time.monotonic,
    ) -> None:
        self._player = player
        # A monotonic clock, injected so a test can press back twice without
        # waiting. It measures the gap between two presses and nothing else.
        self._now = now
        self._last_back: float | None = None
        self._queue = Queue()
        self._album_order: tuple[Track, ...] = ()
        self._ordering = ordering
        self._volume = UNITY_VOLUME
        self._muted = False
        self._shuffled = False
        self._repeating = False

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

    def set_volume(self, level: float) -> None:
        """Set output gain, where 0.0 is silence and 1.0 is unattenuated.

        Held here as well as passed on, so a volume chosen before anything is
        loaded still applies to whatever is loaded next. A level chosen while
        muted is stored without breaking the silence: mute is a switch of its
        own, so nothing but that switch turns it off.
        """
        self._volume = level
        self._player.set_volume(self._audible_level)

    @property
    def volume(self) -> float:
        """The gain chosen, whether or not it is currently being heard."""
        return self._volume

    @property
    def muted(self) -> bool:
        """Whether output is held silent regardless of the level chosen."""
        return self._muted

    def set_muted(self, muted: bool) -> None:
        """Silence the output, else return it to the level already chosen."""
        self._muted = muted
        self._player.set_volume(self._audible_level)

    @property
    def _audible_level(self) -> float:
        """What the device is asked for: nothing at all while muted."""
        return SILENT_VOLUME if self._muted else self._volume

    @property
    def shuffled(self) -> bool:
        """Whether the queue is running in an arbitrary order."""
        return self._shuffled

    def set_shuffled(self, shuffled: bool) -> None:
        """Scatter the queue, else put it back into the album's own order.

        What is playing keeps playing either way: changing the order of what
        comes next is no reason to interrupt the track in hand. Scattering
        leads with that track, so next reaches the whole of the rest of the
        album rather than whatever the new order left after it.
        """
        self._shuffled = shuffled
        if not self._album_order:
            return
        if not shuffled:
            self._queue = self._queue.reordered(self._album_order)
            return
        self._queue = self._queue.reordered_leading(self._ordering(self._album_order))

    @property
    def repeating(self) -> bool:
        """Whether the queue starts again rather than ending."""
        return self._repeating

    def set_repeating(self, repeating: bool) -> None:
        """Choose between the queue ending at its last track and looping."""
        self._repeating = repeating

    def play_album(self, album: Album, first: Track) -> None:
        """Queue an album and start at the track that was activated.

        The album's own order is kept beside the queue, because it is the only
        thing shuffle can be switched back to.
        """
        self._album_order = album.ordered_tracks()
        self._queue = queue_from(self._album_order, first)
        if self._shuffled:
            self._queue = self._queue.reordered_leading(
                self._ordering(self._album_order)
            )
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
        """Play the following track; what the end does depends on repeat.

        A repeating queue of one track wraps round to that same track, which
        means playing it again rather than doing nothing.
        """
        if self._repeating:
            self._restart_at(self._queue.wrapped_next())
            return
        self._move(self._queue.next())

    def previous(self) -> None:
        """Start this track again, unless back was pressed a moment ago too.

        While a track is playing, back means starting that track again: that
        is what somebody who has heard enough of it to reach for the button
        meant by it. Pressing back again straight afterwards means the track
        before, started at ITS beginning, so quick repeated presses walk back
        through the album while a single press never leaves it.

        Under shuffle it always means starting again. The queue then runs in a
        scattered order rather than the order the listener heard, so the track
        lying behind the playhead is not the one they would be asking for.
        Anything played before the shuffle was switched on is not in the run at
        all. Offering a step back there would be answering a different question
        from the one asked.
        """
        again = self._pressed_back_again()
        if self._shuffled or not again:
            self._restart_at(self._queue)
            return
        if self._repeating:
            self._restart_at(self._queue.wrapped_previous())
            return
        self._move(self._queue.previous())

    def _pressed_back_again(self) -> bool:
        """Whether this press of back followed hard on the heels of the last.

        The gap is measured between the presses rather than from where the
        track has reached, because a reported position is the one thing here
        that depends on a device being open and feeding.
        """
        pressed = self._now()
        earlier = self._last_back
        self._last_back = pressed
        if earlier is None:
            return False
        return (pressed - earlier) * MILLISECONDS_PER_SECOND <= QUICK_PRESS_MS

    def _move(self, moved: Queue) -> None:
        """Take up a new position, unless it is the position already held."""
        if moved == self._queue:
            return
        self._restart_at(moved)

    def _restart_at(self, moved: Queue) -> None:
        """Take up a position and play it, whether or not it is a new one."""
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
        if not self._queue.has_next and not self._repeating:
            self._player.stop()
            return True
        self.next()
        return True

    def _load_current(self) -> None:
        """Open the current track and start it. Nothing to open is not a fault."""
        track = self._queue.current
        if track is None:
            return
        self._player.set_volume(self._audible_level)
        self._player.load(
            track.source,
            OutputRequest(sample_rate=track.sample_rate, bit_depth=track.bit_depth),
        )
        self._player.play()
