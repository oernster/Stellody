"""What back means, which depends on whether it was just pressed already.

While a track is playing, back starts that track again. Pressing it again
straight afterwards means the track before, started at its own beginning, so
quick repeated presses walk back through the album while a single press never
leaves the track in hand.

The gap is measured between the presses, on an injected monotonic clock, so
these tests press twice without waiting. It was measured from the position the
device reported at first; that reading depends on a device being open and
feeding, so in a real run back stepped back every time.

Under shuffle back always restarts. The queue then runs scattered rather than
in the order the listener heard it, so the track behind the playhead is not
the one they would be asking for.
"""

from __future__ import annotations

from transport_support import FakePlayer, album_of, reversed_order, track

from stellody.application.transport import QUICK_PRESS_MS, Transport
from stellody.domain.track import MILLISECONDS_PER_SECOND

# Either side of the window, named rather than written into each test.
SOON_MS = QUICK_PRESS_MS - 1
LATER_MS = QUICK_PRESS_MS + 1


class Hand:
    """A clock the tests move themselves, in whole milliseconds."""

    def __init__(self) -> None:
        self.elapsed_ms = 0

    def __call__(self) -> float:
        """The reading now, in seconds, as time.monotonic reports it."""
        return self.elapsed_ms / MILLISECONDS_PER_SECOND

    def advance(self, milliseconds: int) -> None:
        """Move the clock on."""
        self.elapsed_ms += milliseconds


def playing_the_middle_track():
    """A transport playing the middle track of three, with a clock to hand."""
    tracks = (track(1), track(2), track(3))
    player = FakePlayer()
    clock = Hand()
    transport = Transport(player, ordering=reversed_order, now=clock)
    transport.play_album(album_of(*tracks), tracks[1])
    player.calls.clear()
    player.loaded.clear()
    return transport, player, clock, tracks


def test_back_while_a_track_plays_starts_that_track_again() -> None:
    """However long it has been playing, one press never leaves the track."""
    transport, player, clock, tracks = playing_the_middle_track()
    clock.advance(LATER_MS * 100)
    transport.previous()
    assert transport.current is tracks[1], "the same track, not the one before"
    assert player.loaded == [tracks[1].source], "and opened again from its start"
    assert player.calls == ["load", "play"]


def test_back_pressed_again_straight_after_steps_to_the_track_before() -> None:
    transport, player, clock, tracks = playing_the_middle_track()
    transport.previous()
    assert transport.current is tracks[1], "the first press restarted it"
    clock.advance(SOON_MS)
    transport.previous()
    assert transport.current is tracks[0], "the second press stepped back"
    assert player.loaded[-1] == tracks[0].source, "started at its own beginning"


def test_back_pressed_again_much_later_starts_the_track_again() -> None:
    """A press minutes after the last one is a fresh press, not a second one."""
    transport, _, clock, tracks = playing_the_middle_track()
    transport.previous()
    clock.advance(LATER_MS)
    transport.previous()
    assert transport.current is tracks[1]


def test_pressing_back_repeatedly_walks_back_through_the_album() -> None:
    """Each press restarts the clock, so a third quick press steps again."""
    transport, _, clock, tracks = playing_the_middle_track()
    transport.next()
    assert transport.current is tracks[2]
    for _ in range(3):
        transport.previous()
        clock.advance(SOON_MS)
    assert transport.current is tracks[0], "restarted, then stepped back twice"


def test_back_while_shuffled_always_starts_the_track_again() -> None:
    """However quickly it is pressed, whatever the scatter left behind."""
    transport, _, clock, _tracks = playing_the_middle_track()
    transport.set_shuffled(True)
    transport.next()
    landed = transport.current
    for _ in range(3):
        transport.previous()
        clock.advance(SOON_MS)
    assert transport.current is landed, "never stepped back"


def test_back_at_the_start_of_a_repeating_queue_wraps_to_its_end() -> None:
    """Repeat still decides what lies before the first track."""
    transport, _, clock, tracks = playing_the_middle_track()
    transport.previous()
    clock.advance(SOON_MS)
    transport.previous()
    assert transport.current is tracks[0]
    transport.set_repeating(True)
    clock.advance(SOON_MS)
    transport.previous()
    assert transport.current is tracks[2]
