"""Where a queue move lands, decided apart from the device that plays it.

Every rule here is a pure function of a queue and the two switches that bend
it, so what Next means under repeat and shuffle can be read in one place and
tested without a device. The transport applies these answers; it does not work
them out.

Randomness enters as an argument, exactly as time does elsewhere in this
layer: an ordering arrives already chosen, so nothing here holds a source of
its own.
"""

from __future__ import annotations

from collections.abc import Callable

from stellody.domain.playback import RepeatMode
from stellody.domain.queue import Queue
from stellody.domain.track import Track

# Below this there is nothing to scatter and no join to avoid: one track
# repeating is that track again, which is what repeat means there.
SHUFFLE_NEEDS = 2

Ordering = Callable[[tuple[Track, ...]], tuple[Track, ...]]


def without_a_join(queue: Queue, order: tuple[Track, ...]) -> tuple[Track, ...]:
    """The same order, not starting on the track that has just played.

    Hearing one track twice across the join is the one repeat nobody means.
    """
    playing = queue.current
    if playing is None or order[0] is not playing:
        return order
    first, second, *rest = order
    return (second, first, *rest)


def begun_again(
    queue: Queue,
    album_order: tuple[Track, ...],
    shuffled: bool,
    ordering: Ordering,
) -> Queue:
    """The queue for an album starting over, which is what repeat repeats.

    Shuffled, the album is scattered afresh rather than replayed in the order
    it happened to take last time: a shuffle handing back the same running
    order every time round is a fixed order with extra steps.
    """
    if not shuffled or len(album_order) < SHUFFLE_NEEDS:
        return queue.wrapped_next()
    return Queue(without_a_join(queue, ordering(album_order)), 0)


def after_next(
    queue: Queue,
    repeat: RepeatMode,
    shuffled: bool,
    album_order: tuple[Track, ...],
    ordering: Ordering,
) -> Queue:
    """Where pressing Next lands, which repeat bends at the end of a queue.

    A repeating queue of one track wraps round to that same track, which means
    playing it again rather than doing nothing. Next advances under every mode,
    holding one track included: a listener who has asked to move on has asked
    to move on.
    """
    if not repeat.repeats:
        return queue.next()
    if queue.has_next:
        return queue.wrapped_next()
    return begun_again(queue, album_order, shuffled, ordering)


def after_previous(
    queue: Queue,
    repeat: RepeatMode,
    shuffled: bool,
    waiting_at_the_start: bool,
) -> Queue:
    """Where pressing Back lands, which is usually the track already in hand.

    Back means the beginning of this track while it is playing; pressing it
    again where it is already waiting there means the track before. Under
    shuffle it always means this track, since the run is not the order the
    listener heard and the track behind the playhead is not the one they are
    asking for.
    """
    if shuffled or not waiting_at_the_start:
        return queue
    if repeat.repeats:
        return queue.wrapped_previous()
    return queue.previous()


def follower_queue(queue: Queue, repeat: RepeatMode, shuffled: bool) -> Queue | None:
    """The position that will follow this one, when it can be known already.

    Gapless playback needs the next source decoding before the current one
    ends, so something has to say what it will be while the current track is
    still playing. That is only answerable where the answer cannot change: a
    scattered album beginning again picks its order at the moment it begins,
    so there is deliberately nothing to line up there and the seam is honest.
    """
    if queue.current is None:
        return None
    if repeat is RepeatMode.ONE:
        return queue
    if queue.has_next:
        return queue.next()
    if repeat.repeats and not shuffled:
        return queue.wrapped_next()
    return None


def reordered_for(
    queue: Queue, album_order: tuple[Track, ...], shuffled: bool, ordering: Ordering
) -> Queue:
    """The queue under the order the shuffle switch now asks for.

    What is playing keeps playing either way: changing the order of what
    comes next is no reason to interrupt the track in hand. Scattering leads
    with that track, so next reaches the whole of the rest of the album
    rather than whatever the new order happened to leave after it.
    """
    if not shuffled:
        return queue.reordered(album_order)
    return queue.reordered_leading(ordering(album_order))
