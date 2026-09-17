"""Stepping through the queue: Next, Back and taking up where they land.

One concern rather than two methods that happen to sit together: both change
WHICH track is in hand, neither has an opinion about the stream and both end
in the same load. Kept beside `queue_order.py` for the same reason that is
kept apart from the transport: shuffle and repeat describe the shape of the
queue, these two walk it and the transport is what holds a device open.

The rules themselves are the domain's, in `domain/moving.py`. What is decided
here is only whether landing somewhere means playing, which is the one part
that depends on how the transport got there.
"""

from __future__ import annotations

from stellody.application.playback_ports import PlaybackPort
from stellody.domain.moving import (
    Ordering,
    RepeatMode,
    after_next,
    after_previous,
)
from stellody.domain.queue import Queue
from stellody.domain.track import Track


class Stepping:
    """Next and Back, as a transport carries them. Mixed into `Transport`."""

    _player: PlaybackPort
    _queue: Queue
    _repeat: RepeatMode
    _shuffled: bool
    _album_order: tuple[Track, ...]
    _ordering: Ordering
    _waiting_at_the_start: bool

    def next(self) -> None:
        """Play the following track; what the end does depends on repeat.

        This is the deliberate skip, so it advances under every mode, holding
        one track included. A listener who has asked to move on has asked to
        move on; a repeat that swallowed the request would leave them pressing
        a button that does nothing and no way off the track but the switch.

        Where the move lands is `domain.moving.after_next`; this decides
        only whether landing there means playing.

        Skipping while paused stays paused. Somebody hunting for the track
        they want has said one thing, that they want silence; pressing
        Next is not taking it back, it started playing anyway, which is what
        this passes the state along to prevent.
        """
        self._move_on(playing=self.playing)

    def _move_on(self, playing: bool) -> None:
        """Step to the following track, playing it or waiting on it.

        The one place that decides where Next lands. Whether it plays is
        handed IN rather than read here, because the two callers disagree and
        must: a listener pressing Next keeps whatever state they were in,
        while a track that has played out carries on into the next one. Read
        from the device instead, the second would break, since a device that
        has run out of track reports itself paused exactly as a paused one
        does; the album would then stop dead at every boundary.
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
        self._restart_at(moved, playing)

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

    def _restart_at(self, moved: Queue, playing: bool = True) -> None:
        """Take up a position, playing it unless told to wait on it.

        Never counted as waiting at a beginning, whether it plays or not.
        Waiting there is what pressing Back does and it is what a second Back
        reads to mean the track before; arriving somewhere by SKIPPING is not
        that, even when it arrives quietly. Conflating the two made Back after
        a skip jump a track instead of returning to the start of the one in
        hand.
        """
        self._queue = moved
        self._load_current(playing=playing, waiting=False)

    def _open_paused(self, moved: Queue) -> None:
        """Take up a position at its beginning, waiting rather than playing.

        Opening a source leaves the device paused at its first frame, so this
        is the load without the play that every other move makes.
        """
        self._queue = moved
        self._load_current(playing=False)
