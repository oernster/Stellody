"""What back means, which depends on where the transport already is.

While a track is playing, back returns to its beginning and waits there.
Pressing back again while it is already waiting at that beginning means the
track before, waiting at its beginning too, so repeated presses walk back
through the album at whatever pace suits.

What decides between the two is a state rather than a stopwatch. Two earlier
attempts measured time instead and both failed in the hand: judging it by the
position the device reported meant back stepped back on every press, since a
reported position needs a device open and feeding; judging it by the gap
between two presses meant a deliberate second press restarted the track, so
going back a track took five to ten presses until two landed inside the window.

Under shuffle back always returns to the start of the track in hand. The queue
then runs scattered rather than in the order the listener heard, so the track
behind the playhead is not the one they would be asking for.
"""

from __future__ import annotations

from transport_support import FakePlayer, album_of, reversed_order, track

from stellody.application.transport import Transport
from stellody.domain.playback import RepeatMode


def playing_the_middle_track():
    """A transport playing the middle track of three."""
    tracks = (track(1), track(2), track(3))
    player = FakePlayer()
    transport = Transport(player, ordering=reversed_order)
    transport.play_album(album_of(*tracks), tracks[1])
    player.calls.clear()
    player.loaded.clear()
    return transport, player, tracks


def test_back_while_a_track_plays_returns_to_its_beginning_and_waits() -> None:
    transport, player, tracks = playing_the_middle_track()
    transport.previous()
    assert transport.current is tracks[1], "the same track, not the one before"
    assert player.loaded == [tracks[1].source], "opened again from its start"
    assert player.calls == ["load"], "opened, not played on"
    assert transport.playing is False, "it waits at the beginning"


def test_back_again_while_waiting_there_goes_to_the_track_before() -> None:
    transport, player, tracks = playing_the_middle_track()
    transport.previous()
    transport.previous()
    assert transport.current is tracks[0]
    assert transport.playing is False, "waiting at its beginning too"
    assert player.calls == ["load", "load"]


def test_back_again_however_long_afterwards_still_goes_to_the_track_before() -> None:
    """Measured against a real complaint: this took five to ten presses.

    Nothing here advances a clock, which is the point. The transport is left
    waiting at the beginning between the two presses and there is no window
    for the second one to miss.
    """
    transport, _, tracks = playing_the_middle_track()
    transport.previous()
    transport.previous()
    assert transport.current is tracks[0]


def test_pressing_back_repeatedly_walks_back_through_the_album() -> None:
    transport, _, tracks = playing_the_middle_track()
    transport.next()
    assert transport.current is tracks[2]
    reached = []
    for _ in range(3):
        transport.previous()
        reached.append(transport.current)
    assert reached == [tracks[2], tracks[1], tracks[0]], "the start, then back twice"


def test_playing_on_again_makes_the_next_press_a_fresh_one() -> None:
    """Once the music is running the transport is no longer at the start."""
    transport, _, tracks = playing_the_middle_track()
    transport.previous()
    transport.toggle()
    assert transport.playing is True
    transport.previous()
    assert transport.current is tracks[1], "back to the start, not to track one"


def test_a_track_reached_by_any_other_means_is_not_waiting_at_its_start() -> None:
    """Next opens a track and plays it on, so back after it means its start."""
    transport, _, tracks = playing_the_middle_track()
    transport.previous()
    transport.next()
    assert transport.current is tracks[2]
    transport.previous()
    assert transport.current is tracks[2], "its own beginning, not track two"


def test_back_while_shuffled_always_returns_to_the_start_of_the_track() -> None:
    """However often it is pressed, whatever the scatter left behind it."""
    transport, _, _tracks = playing_the_middle_track()
    transport.set_shuffled(True)
    transport.next()
    landed = transport.current
    for _ in range(5):
        transport.previous()
    assert transport.current is landed, "never stepped back"


def test_back_at_the_start_of_a_repeating_queue_wraps_to_its_end() -> None:
    """Repeat still decides what lies before the first track."""
    transport, _, tracks = playing_the_middle_track()
    transport.previous()
    transport.previous()
    assert transport.current is tracks[0]
    transport.set_repeat(RepeatMode.ALBUM)
    transport.previous()
    assert transport.current is tracks[2]
