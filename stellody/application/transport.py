"""Playing a queue through whatever device is behind the playback port.

The window presses buttons; this decides what they mean. It owns the queue and
the rule that ties the queue to the device: loading a track leaves it playing,
because nothing else is what pressing next means. Back is the one exception;
it says why where it is written.

No Qt, no device, no filesystem. The port is the only way out.
"""

from __future__ import annotations

import random
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
from stellody.domain.track import Track

Ordering = Callable[[tuple[Track, ...]], tuple[Track, ...]]

# Below this there is nothing to scatter and no join to avoid: one track
# repeating is that track again, which is what repeat means there.
SHUFFLE_NEEDS = 2


def scattered(tracks: tuple[Track, ...]) -> tuple[Track, ...]:
    """These tracks in an arbitrary order. The default way shuffle shuffles."""
    return tuple(random.sample(tracks, len(tracks)))


class Transport:
    """The transport the window drives: a queue, plus a device to play it on."""

    def __init__(self, player: PlaybackPort, ordering: Ordering = scattered) -> None:
        self._player = player
        # Whether back has already been pressed and is waiting at the start of
        # the track. It is what tells a second press to leave the track; it is
        # a state rather than a stopwatch, because two presses timed against
        # each other made the user hammer the button to land two inside the
        # window.
        self._waiting_at_the_start = False
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
        self._waiting_at_the_start = False
        if self._player.state is PlaybackState.PLAYING:
            self._player.pause()
            return
        if self._player.state is PlaybackState.PAUSED:
            self._player.play()
            return
        self._load_current()

    def stop(self) -> None:
        """Give the device back, keeping the queue where it is."""
        self._waiting_at_the_start = False
        self._player.stop()

    def next(self) -> None:
        """Play the following track; what the end does depends on repeat.

        A repeating queue of one track wraps round to that same track, which
        means playing it again rather than doing nothing.
        """
        if self._repeating and not self._queue.has_next:
            self._begin_again()
            return
        if self._repeating:
            self._restart_at(self._queue.wrapped_next())
            return
        self._move(self._queue.next())

    def _begin_again(self) -> None:
        """Start the album over, which is what repeat repeats.

        Shuffled, the album is scattered afresh rather than replayed in the
        order it happened to take last time: a shuffle that hands back the
        same running order every time round is a fixed order with extra
        steps. The track just heard is kept off the front of the new run,
        since hearing it twice over the join is the one repeat nobody means.
        """
        if not self._shuffled or len(self._album_order) < SHUFFLE_NEEDS:
            self._restart_at(self._queue.wrapped_next())
            return
        self._queue = Queue(self._without_a_join(self._ordering(self._album_order)), 0)
        self._load_current()

    def _without_a_join(self, order: tuple[Track, ...]) -> tuple[Track, ...]:
        """The same order, not starting on the track that has just played."""
        playing = self._queue.current
        if playing is None or order[0] is not playing:
            return order
        first, second, *rest = order
        return (second, first, *rest)

    def previous(self) -> None:
        """Return to the start of this track; leave it if already there.

        While a track is playing, back means the beginning of that track: it
        is what somebody who has heard enough of it to reach for the button
        meant by it. It lands there and waits rather than playing on, so the
        moment to carry on belongs to the listener.

        Pressing back again while it is already waiting at that beginning
        means the track before, waiting at ITS beginning, so repeated presses
        walk back through the album at whatever pace suits. What decides
        between the two is where the transport already is, not how quickly the
        button was pressed twice: a window timed between presses made a
        deliberate second press restart the track instead, so going back a
        track meant hammering the button until two landed inside it.

        Under shuffle it always means the start of the track in hand. The
        queue then runs in a scattered order rather than the order the listener
        heard, so the track lying behind the playhead is not the one they would
        be asking for. Anything played before the shuffle was switched on is
        not in the run at all. Offering a step back there would be answering a
        different question from the one asked.
        """
        if self._shuffled or not self._waiting_at_the_start:
            self._open_paused(self._queue)
            return
        if self._repeating:
            self._open_paused(self._queue.wrapped_previous())
            return
        self._open_paused(self._queue.previous())

    def _move(self, moved: Queue) -> None:
        """Take up a new position, unless it is the position already held."""
        if moved == self._queue:
            return
        self._restart_at(moved)

    def _restart_at(self, moved: Queue) -> None:
        """Take up a position and play it, whether or not it is a new one."""
        self._queue = moved
        self._load_current()

    def _open_paused(self, moved: Queue) -> None:
        """Take up a position at its beginning, waiting rather than playing.

        Opening a source leaves the device paused at its first frame, so this
        is the load without the play that every other move makes.
        """
        self._queue = moved
        self._load_current(playing=False)

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

    def _load_current(self, playing: bool = True) -> None:
        """Open the current track and start it. Nothing to open is not a fault."""
        track = self._queue.current
        if track is None:
            return
        # Anything that opens a track and plays it on has left the start
        # behind; anything that opens one and waits is sitting on it.
        self._waiting_at_the_start = not playing
        self._player.set_volume(self._audible_level)
        self._player.load(
            track.source,
            OutputRequest(sample_rate=track.sample_rate, bit_depth=track.bit_depth),
        )
        if playing:
            self._player.play()
