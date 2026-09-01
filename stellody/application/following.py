"""What the device has been told to run into next, plus whether it has.

Gapless playback moves the decision about the next track earlier: it has to be
open and decoding while the current one is still playing, because the only
thing awake at the seam is the feeder thread inside the engine. Nothing asks it
to advance and nothing loads anything; it simply runs on.

So this holds the two facts that follow from that. What was lined up is KEPT
rather than worked out again, because the switches may move between lining a
track up and the device reaching it; the queue must land where the device
actually went rather than where the rules would send it now. How many seams
have been crossed is a COUNT rather than a signal, so a caller that was not
looking at the moment it happened still learns about it.
"""

from __future__ import annotations

from stellody.application.ports import PlaybackPort
from stellody.domain.moving import follower_queue
from stellody.domain.playback import RepeatMode
from stellody.domain.queue import Queue


class Following:
    """The follower lined up on the device, plus the seams it has crossed."""

    def __init__(self, player: PlaybackPort) -> None:
        self._player = player
        self._lined_up: Queue | None = None
        self._seen = 0

    def restart(self) -> None:
        """Begin counting again, which a freshly loaded source starts from."""
        self._seen = 0
        self._lined_up = None

    def line_up(self, queue: Queue, repeat: RepeatMode, shuffled: bool) -> None:
        """Tell the device what follows, so it is decoded before it is needed.

        A follower that cannot be known yet is cleared rather than guessed at,
        which leaves that one seam honestly gapped instead of landing on the
        wrong track.
        """
        self._lined_up = follower_queue(queue, repeat, shuffled)
        following = None if self._lined_up is None else self._lined_up.current
        self._player.queue_next(None if following is None else following.source)

    def crossed(self) -> Queue | None:
        """Where the device has already run to on its own; None if nowhere.

        A count that has gone UP is the test, rather than one that differs:
        stopping drops the session the count lives on, so a device with nothing
        loaded reports none and must not read as having moved.
        """
        crossings = self._player.crossings
        if crossings <= self._seen or self._lined_up is None:
            return None
        self._seen = crossings
        return self._lined_up
