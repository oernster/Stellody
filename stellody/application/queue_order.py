"""How the queue is ordered, plus what reaching the end of it means.

Shuffle and repeat are one concern: neither disturbs what is playing, both
describe the shape of the queue rather than the stream, while both end in
the same line telling the device what to run into next. The function that does the
scattering sits here too, since a shuffle order and the switch that asks for
one are the same subject.
"""

from __future__ import annotations

import random

from stellody.domain.moving import Ordering, RepeatMode, reordered_for
from stellody.domain.queue import Queue
from stellody.domain.track import Track


def scattered(tracks: tuple[Track, ...]) -> tuple[Track, ...]:
    """These tracks in an arbitrary order. The default way shuffle shuffles."""
    return tuple(random.sample(tracks, len(tracks)))


class QueueOrder:
    """Shuffle and repeat, as a transport carries them. Mixed into `Transport`."""

    _shuffled: bool
    _repeat: RepeatMode
    _queue: Queue
    _album_order: tuple[Track, ...]
    _ordering: Ordering

    def _line_up(self) -> None:
        """Told by the transport; declared here so this file reads on its own."""
        raise NotImplementedError

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
