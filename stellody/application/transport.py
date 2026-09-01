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

from stellody.application.following import Following
from stellody.application.ports import PlaybackPort
from stellody.domain.album import Album
from stellody.domain.moving import (
    Ordering,
    after_next,
    after_previous,
    reordered_for,
)
from stellody.domain.playback import (
    Loudness,
    OutputRequest,
    PlaybackPosition,
    PlaybackState,
    RepeatMode,
    audible_position,
)
from stellody.domain.queue import Queue, queue_from
from stellody.domain.track import Track

# Told the album and the track that has just played out, so a count of complete
# plays can be kept by somebody who is not the transport. The album comes with
# it because a record is kept against an album's identity and because a track
# that has just ended may already be gone from the library that a rescan
# rebuilt underneath it.
PlayedOut = Callable[[Album, Track], None]


def scattered(tracks: tuple[Track, ...]) -> tuple[Track, ...]:
    """These tracks in an arbitrary order. The default way shuffle shuffles."""
    return tuple(random.sample(tracks, len(tracks)))


class Transport:
    """The transport the window drives: a queue, plus a device to play it on."""

    def __init__(
        self,
        player: PlaybackPort,
        ordering: Ordering = scattered,
        played: PlayedOut = lambda _album, _track: None,
    ) -> None:
        self._player = player
        # What the device has been told to run into next. Gapless
        # transitions happen inside the engine, so this is how the queue
        # finds out where the music already went.
        self._following = Following(player)
        # Told when a track has played out, which is the one thing this class
        # is in a position to know: nothing else can see the difference
        # between a track that ended and one somebody skipped.
        self._played = played
        # Whether back has already been pressed and is waiting at the start of
        # the track. It is what tells a second press to leave the track; it is
        # a state rather than a stopwatch, because two presses timed against
        # each other made the user hammer the button to land two inside the
        # window.
        self._waiting_at_the_start = False
        self._queue = Queue()
        self._album: Album | None = None
        self._album_order: tuple[Track, ...] = ()
        self._ordering = ordering
        self._loudness = Loudness()
        self._shuffled = False
        self._repeat = RepeatMode.OFF

    def report_plays_to(self, played: PlayedOut) -> None:
        """Say who is told when a track plays out.

        Set rather than injected, which is the one place this application
        does that; ARCHITECTURE.md records why.
        """
        self._played = played

    @property
    def queue(self) -> Queue:
        """What is lined up, plus where in it playback has reached."""
        return self._queue

    @property
    def album(self) -> Album | None:
        """The album the queue was made from; None while nothing is queued."""
        return self._album

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
        """Set output gain, where 0.0 is silence and 1.0 is unattenuated."""
        self._loudness = self._loudness.at(level)
        self._player.set_volume(self._loudness.audible)

    @property
    def volume(self) -> float:
        """The gain chosen, whether or not it is currently being heard."""
        return self._loudness.level

    @property
    def muted(self) -> bool:
        """Whether output is held silent regardless of the level chosen."""
        return self._loudness.muted

    def set_muted(self, muted: bool) -> None:
        """Silence the output, else return it to the level already chosen."""
        self._loudness = self._loudness.silenced(muted)
        self._player.set_volume(self._loudness.audible)

    @property
    def shuffled(self) -> bool:
        """Whether the queue is running in an arbitrary order."""
        return self._shuffled

    def set_shuffled(self, shuffled: bool) -> None:
        """Scatter the queue, else put it back into the album's own order.

        What is playing keeps playing; `domain.moving.reordered_for` holds
        the rule and says why.
        """
        self._shuffled = shuffled
        if self._album_order:
            self._queue = reordered_for(
                self._queue, self._album_order, shuffled, self._ordering
            )
        self._line_up()

    @property
    def repeat(self) -> RepeatMode:
        """What an ending means: stop, start the album again or hold one track."""
        return self._repeat

    def set_repeat(self, repeat: RepeatMode) -> None:
        """Choose what an ending does. Nothing already playing is disturbed."""
        self._repeat = repeat
        self._line_up()

    def play_album(self, album: Album, first: Track) -> None:
        """Queue an album and start at the track that was activated.

        The album's own order is kept beside the queue, because it is the only
        thing shuffle can be switched back to.
        """
        self._album = album
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

    @property
    def position(self) -> PlaybackPosition | None:
        """How far playback has reached, as a listener would say it.

        The correction belongs here rather than in the engine because the
        size of the lead is a property of the device the port opened;
        this is the layer that asks the port anything. It is honest to within
        one buffer; it does not model the device's own latency beyond that.
        """
        reported = self._player.position()
        if reported is None:
            return None
        return audible_position(reported, self._player.lead_frames)

    def seek(self, frame: int) -> None:
        """Move within the track in hand, in frames, clamped to it.

        Asked for in the listener's terms, so it is the audible position that
        lands where they asked; the decode is put one buffer further on, which
        is where it has to be for that to be true a moment later.
        """
        if self._player.position() is None:
            return
        self._waiting_at_the_start = False
        self._player.seek(max(0, frame) + self._player.lead_frames)

    def next(self) -> None:
        """Play the following track; what the end does depends on repeat.

        This is the deliberate skip, so it advances under every mode, holding
        one track included. A listener who has asked to move on has asked to
        move on; a repeat that swallowed the request would leave them pressing
        a button that does nothing and no way off the track but the switch.

        Where the move lands is `domain.moving.after_next`; this decides
        only whether landing there means playing.
        """
        moved = after_next(
            self._queue,
            self._repeat,
            self._shuffled,
            self._album_order,
            self._ordering,
        )
        # Off the end with repeat off there is nowhere to go, so the track
        # in hand is left alone rather than started again.
        if not self._repeat.repeats and moved == self._queue:
            return
        self._restart_at(moved)

    def previous(self) -> None:
        """Return to the start of this track; leave it if already there.

        While a track is playing, back means the beginning of that track: it
        is what somebody who has heard enough of it to reach for the button
        meant by it. It lands there and waits rather than playing on, so the
        moment to carry on belongs to the listener. Pressing back again while
        it waits there means the track before, waiting at ITS beginning.

        What decides between the two is where the transport already is, not
        how quickly the button was pressed twice: a window timed between
        presses made a deliberate second press restart the track instead, so
        going back a track meant hammering the button until two landed inside
        it. `domain.moving.after_previous` holds the rule itself.
        """
        self._open_paused(
            after_previous(
                self._queue,
                self._repeat,
                self._shuffled,
                self._waiting_at_the_start,
            )
        )

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

        Two different endings arrive through this one door. The device may
        have run into the next track by itself, having had it open and
        decoding before the seam: nothing needs loading there and the only
        work is to move the queue to where the music already is. Otherwise a
        track has simply stopped, which is not reported by the device and so
        is asked about.

        Holding one track is decided HERE rather than in `next`, because the
        two are different questions asked through the same door: an ending is
        what repeat is about, while pressing Next is a listener overruling it.
        Only the first of them replays the track.
        """
        crossed = self._following.crossed()
        if crossed is not None:
            self._report_played()
            self._queue = crossed
            self._waiting_at_the_start = False
            self._line_up()
            return True
        if not self._player.finished:
            return False
        self._report_played()
        if self._repeat is RepeatMode.ONE:
            self._restart_at(self._queue)
            return True
        if not self._queue.has_next and not self._repeat.repeats:
            self._player.stop()
            return True
        self.next()
        return True

    def _report_played(self) -> None:
        """Say that the track in hand reached its end, to whoever counts."""
        finished = self._queue.current
        album = self._album
        if finished is not None and album is not None:
            self._played(album, finished)

    def _line_up(self) -> None:
        """Tell the device what to run into when the track in hand ends."""
        self._following.line_up(self._queue, self._repeat, self._shuffled)

    def _load_current(self, playing: bool = True) -> None:
        """Open the current track and start it. Nothing to open is not a fault."""
        track = self._queue.current
        if track is None:
            return
        # Anything that opens a track and plays it on has left the start
        # behind; anything that opens one and waits is sitting on it.
        self._waiting_at_the_start = not playing
        self._player.set_volume(self._loudness.audible)
        self._player.load(
            track.source,
            OutputRequest(sample_rate=track.sample_rate, bit_depth=track.bit_depth),
        )
        self._following.restart()
        self._line_up()
        if playing:
            self._player.play()
