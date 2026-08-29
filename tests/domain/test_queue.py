"""The queue: what plays next, then what happens at either end."""

from __future__ import annotations

import pytest
from factories import make_track

from stellody.domain.queue import Queue, queue_from


def three() -> tuple:
    """Three distinct tracks, in order."""
    return tuple(
        make_track(track_number=number, title=f"Track {number}") for number in (1, 2, 3)
    )


def test_an_empty_queue_has_nothing_current() -> None:
    empty = Queue()
    assert empty.current is None
    assert empty.has_next is False
    assert empty.has_previous is False


def test_a_queue_starts_at_the_track_that_was_activated() -> None:
    tracks = three()
    queue = queue_from(tracks, tracks[1])
    assert queue.current is tracks[1]
    assert queue.has_previous is True
    assert queue.has_next is True


def test_moving_on_and_back_returns_where_it_started() -> None:
    tracks = three()
    queue = queue_from(tracks, tracks[0])
    assert queue.next().current is tracks[1]
    assert queue.next().previous().current is tracks[0]


def test_the_end_of_the_queue_is_not_an_error() -> None:
    """Nowhere further to go is a state, not a failure."""
    tracks = three()
    last = queue_from(tracks, tracks[2])
    assert last.has_next is False
    assert last.next() is last


def test_the_start_of_the_queue_is_not_an_error_either() -> None:
    tracks = three()
    first = queue_from(tracks, tracks[0])
    assert first.has_previous is False
    assert first.previous() is first


def test_a_track_that_is_not_in_the_queue_moves_nothing() -> None:
    tracks = three()
    queue = queue_from(tracks, tracks[0])
    assert queue.at(make_track(title="Elsewhere")) is queue


def test_two_identical_tracks_are_told_apart_by_which_was_activated() -> None:
    """A library may hold the same track twice; the one clicked is the one."""
    twin = make_track(title="Twin")
    other = make_track(title="Twin")
    queue = queue_from((twin, other), other)
    assert queue.index == 1
    assert queue.current is other


def test_a_position_outside_the_queue_is_refused() -> None:
    tracks = three()
    with pytest.raises(ValueError, match="past the end"):
        Queue(tracks, len(tracks))
    with pytest.raises(ValueError, match="before the start"):
        Queue(tracks, -2)


def test_moving_never_alters_the_queue_it_was_asked_of() -> None:
    tracks = three()
    queue = queue_from(tracks, tracks[0])
    queue.next()
    assert queue.current is tracks[0]
