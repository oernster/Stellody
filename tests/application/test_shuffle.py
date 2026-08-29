"""Shuffle: what it reorders, what it leads with and what next then reaches.

The rule that matters is not that the order changes. It is that the track in
hand leads the scattered run, so pressing next reaches the whole of the rest
of the album. Before that rule existed the playing track kept whatever place
the scatter gave it: measured over 20,000 shuffles of a twelve track album,
next did nothing at all in 8.28% of them, which is the 1 in 12 a uniform
landing spot predicts; on average only 5.5 of the other 11 tracks were still
reachable. The rest were stranded behind the playhead.
"""

from __future__ import annotations

from transport_support import FakePlayer, album_of, reversed_order, track

from stellody.application.transport import Transport, scattered

# Enough tracks that a scatter which happened to be the album order would not
# pass by luck.
LONG_ALBUM = 12


def test_shuffling_reorders_the_queue_and_keeps_playing_what_was_playing() -> None:
    one, two, three = track(1), track(2), track(3)
    player = FakePlayer()
    transport = Transport(player, ordering=reversed_order)
    transport.play_album(album_of(one, two, three), two)
    player.calls.clear()
    transport.set_shuffled(True)
    assert transport.shuffled is True
    assert transport.queue.tracks == (two, three, one), "what plays leads the run"
    assert transport.current is two
    assert player.calls == [], "reordering what comes next interrupts nothing"


def test_shuffling_leaves_the_whole_of_the_rest_of_the_album_ahead() -> None:
    """The defect this rule exists for: next had nowhere to go."""
    tracks = tuple(track(number) for number in range(1, LONG_ALBUM + 1))
    transport = Transport(FakePlayer(), ordering=reversed_order)
    transport.play_album(album_of(*tracks), tracks[0])
    transport.set_shuffled(True)
    reached = [transport.current]
    while transport.queue.has_next:
        transport.next()
        reached.append(transport.current)
    assert reached[0] is tracks[0], "starting where it was already playing"
    assert set(reached) == set(tracks), "every track is still reachable"
    assert len(reached) == len(tracks), "and none of them twice"


def test_next_follows_the_shuffled_order_rather_than_the_album_order() -> None:
    """Shuffle is about what comes next; anything else is just a reordering."""
    one, two, three, four = track(1), track(2), track(3), track(4)
    transport = Transport(FakePlayer(), ordering=reversed_order)
    transport.play_album(album_of(one, two, three, four), one)
    transport.set_shuffled(True)
    transport.next()
    assert transport.current is four, "the scattered order, not track two"


def test_unshuffling_puts_the_album_back_into_its_own_order() -> None:
    one, two, three = track(1), track(2), track(3)
    transport = Transport(FakePlayer(), ordering=reversed_order)
    transport.play_album(album_of(one, two, three), one)
    transport.set_shuffled(True)
    transport.set_shuffled(False)
    assert transport.queue.tracks == (one, two, three)
    assert transport.current is one


def test_shuffle_chosen_before_anything_plays_applies_to_the_next_album() -> None:
    """The switch is remembered, so it does not have to be pressed twice."""
    one, two, three = track(1), track(2), track(3)
    transport = Transport(FakePlayer(), ordering=reversed_order)
    transport.set_shuffled(True)
    assert transport.queue.tracks == ()
    transport.play_album(album_of(one, two, three), two)
    assert transport.queue.tracks == (two, three, one), "led by what was activated"
    assert transport.current is two


def test_the_default_shuffle_keeps_every_track_and_loses_none() -> None:
    """The real one is random, so what is asserted is what it preserves."""
    tracks = tuple(track(number) for number in range(1, 6))
    transport = Transport(FakePlayer())
    transport.play_album(album_of(*tracks), tracks[0])
    transport.set_shuffled(True)
    assert set(transport.queue.tracks) == set(tracks)
    assert len(transport.queue.tracks) == len(tracks)
    assert transport.current is tracks[0]


def test_the_default_shuffle_is_a_scatter_and_not_a_fixed_rearrangement() -> None:
    """A reversal or a rotation would satisfy every assertion above."""
    tracks = tuple(track(number) for number in range(1, LONG_ALBUM + 1))
    seen = {scattered(tracks) for _ in range(LONG_ALBUM)}
    assert len(seen) > 1, "the same order every time is not a shuffle"
    assert all(set(order) == set(tracks) for order in seen), "and it loses nothing"
