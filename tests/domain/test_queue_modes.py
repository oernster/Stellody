"""Wrapping round the ends; running the same tracks in another order.

These are the two things repeat and shuffle need from a queue. Both are pure
moves on a value: the order arrives from outside, so nothing here reaches for
a source of randomness.
"""

from __future__ import annotations

import pytest

from stellody.domain.queue import Queue
from stellody.domain.track import CD_SAMPLE_RATE, Track, TrackSource


def track(number: int) -> Track:
    """One ordinary track of an album."""
    return Track(
        source=TrackSource(path=f"{number}.flac"),
        disc_number=1,
        track_number=number,
        title=f"Track {number}",
        artists=("Holst",),
        duration_ms=1000,
        sample_rate=CD_SAMPLE_RATE,
        bit_depth=16,
    )


def test_the_end_of_a_wrapping_queue_is_its_own_beginning() -> None:
    one, two = track(1), track(2)
    queue = Queue((one, two), 1)
    assert queue.wrapped_next().current is one


def test_the_beginning_of_a_wrapping_queue_is_its_own_end() -> None:
    one, two = track(1), track(2)
    queue = Queue((one, two), 0)
    assert queue.wrapped_previous().current is two


def test_a_single_track_wraps_round_to_itself_in_both_directions() -> None:
    """Which is what playing one track on repeat has to mean."""
    one = track(1)
    queue = Queue((one,), 0)
    assert queue.wrapped_next().current is one
    assert queue.wrapped_previous().current is one


def test_an_empty_queue_wraps_to_nothing_rather_than_failing() -> None:
    """There is no position to move from, so both moves are simply no moves."""
    empty = Queue()
    assert empty.wrapped_next() is empty
    assert empty.wrapped_previous() is empty


def test_reordering_keeps_playing_what_was_playing() -> None:
    one, two, three = track(1), track(2), track(3)
    queue = Queue((one, two, three), 1)
    moved = queue.reordered((three, two, one))
    assert moved.current is two
    assert moved.tracks == (three, two, one)


def test_reordering_an_idle_queue_simply_takes_the_new_order() -> None:
    """Nothing is playing, so there is nothing for the move to preserve."""
    one, two = track(1), track(2)
    moved = Queue((one, two)).reordered((two, one))
    assert moved.tracks == (two, one)
    assert moved.current is None


def test_an_order_missing_the_current_track_is_refused() -> None:
    """Silently switching to a different track is the one unacceptable move."""
    one, two = track(1), track(2)
    queue = Queue((one, two), 0)
    with pytest.raises(ValueError, match="keep the track that is current"):
        queue.reordered((two,))


def test_reordering_that_leads_puts_what_is_playing_at_the_head() -> None:
    """So the whole of the rest of the run is still ahead of the playhead."""
    one, two, three = track(1), track(2), track(3)
    queue = Queue((one, two, three), 1)
    moved = queue.reordered_leading((three, two, one))
    assert moved.tracks == (two, three, one)
    assert moved.current is two
    assert moved.index == 0
    assert moved.has_next is True
    assert moved.has_previous is False, "nothing has been played in this run yet"


def test_a_leading_reorder_of_an_idle_queue_simply_takes_the_new_order() -> None:
    """Nothing is playing, so there is no track for the order to lead with."""
    one, two = track(1), track(2)
    moved = Queue((one, two)).reordered_leading((two, one))
    assert moved.tracks == (two, one)
    assert moved.current is None


def test_a_leading_order_missing_the_current_track_is_refused() -> None:
    """The same rule as any other reordering, for the same reason."""
    one, two = track(1), track(2)
    queue = Queue((one, two), 0)
    with pytest.raises(ValueError, match="keep the track that is current"):
        queue.reordered_leading((two,))
