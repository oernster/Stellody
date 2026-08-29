"""What back means, which depends on how far into the track it is pressed.

Part way through a track, back starts that track again. Near the start it
steps to the track before, so pressing it twice in quick succession steps
back: the first press leaves the playhead at the beginning. The judgement is
made on the position the device reports rather than on a clock of our own, so
nothing here reads the time.

Under shuffle back always restarts. The queue then runs scattered rather than
in the order the listener heard it, so the track behind the playhead is not
the one they would be asking for.
"""

from __future__ import annotations

from transport_support import FakePlayer, album_of, reversed_order, track

from stellody.application.transport import RESTART_WINDOW_MS, Transport

# Either side of the window, named rather than written into each test.
WELL_IN_MS = RESTART_WINDOW_MS * 2
JUST_STARTED_MS = RESTART_WINDOW_MS - 1


def playing_the_middle_track(elapsed_ms: int | None):
    """A transport part way through the middle track of three."""
    tracks = (track(1), track(2), track(3))
    player = FakePlayer()
    transport = Transport(player, ordering=reversed_order)
    transport.play_album(album_of(*tracks), tracks[1])
    player.elapsed_ms = elapsed_ms
    player.calls.clear()
    player.loaded.clear()
    return transport, player, tracks


def test_back_part_way_through_a_track_starts_that_track_again() -> None:
    transport, player, tracks = playing_the_middle_track(WELL_IN_MS)
    transport.previous()
    assert transport.current is tracks[1], "the same track, not the one before"
    assert player.loaded == [tracks[1].source], "and opened again from its start"
    assert player.calls == ["load", "play"]


def test_back_near_the_start_of_a_track_steps_to_the_one_before() -> None:
    transport, _, tracks = playing_the_middle_track(JUST_STARTED_MS)
    transport.previous()
    assert transport.current is tracks[0]


def test_a_second_press_straight_after_the_first_steps_back() -> None:
    """The first press left the playhead at the beginning, so the next steps."""
    transport, player, tracks = playing_the_middle_track(WELL_IN_MS)
    transport.previous()
    assert transport.current is tracks[1], "the first press restarted it"
    player.elapsed_ms = 0
    transport.previous()
    assert transport.current is tracks[0], "the second press stepped back"


def test_a_device_that_cannot_say_where_it_is_steps_back() -> None:
    """Reporting nothing is not reporting zero; back keeps its older meaning."""
    transport, _, tracks = playing_the_middle_track(None)
    transport.previous()
    assert transport.current is tracks[0]


def test_back_while_shuffled_always_starts_the_track_again() -> None:
    """However far in, whatever the scattered order left behind it."""
    for elapsed in (None, 0, JUST_STARTED_MS, WELL_IN_MS):
        transport, player, _ = playing_the_middle_track(elapsed)
        transport.set_shuffled(True)
        transport.next()
        landed = transport.current
        player.elapsed_ms = elapsed
        transport.previous()
        assert transport.current is landed, f"stepped back at {elapsed}ms in"


def test_back_at_the_start_of_a_repeating_queue_wraps_to_its_end() -> None:
    """Repeat still decides what lies before the first track."""
    transport, _, tracks = playing_the_middle_track(JUST_STARTED_MS)
    transport.previous()
    assert transport.current is tracks[0]
    transport.set_repeating(True)
    transport.previous()
    assert transport.current is tracks[2]
