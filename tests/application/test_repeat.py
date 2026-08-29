"""What repeat repeats, which is the album rather than the track.

An album that ends starts again from its beginning until repeat is turned off.
Shuffled, it is scattered afresh each time round: a shuffle that hands back the
same running order every time is a fixed order with extra steps. The track just
heard is kept off the front of the new run, since hearing it twice across the
join is the one repeat nobody means by it.
"""

from __future__ import annotations

from transport_support import FakePlayer, album_of, reversed_order, track

from stellody.application.transport import Transport

# Enough tracks that a scatter cannot be mistaken for the album's own order.
LONG_ALBUM = 8


def played_out(transport: Transport, player: FakePlayer, steps: int) -> list[int]:
    """The track numbers heard as one track after another plays to its end."""
    heard = [transport.current.track_number]
    for _ in range(steps):
        player.finished = True
        transport.advance_if_finished()
        heard.append(transport.current.track_number)
    return heard


def test_an_album_that_ends_starts_again_rather_than_stopping() -> None:
    one, two, three = track(1), track(2), track(3)
    player = FakePlayer()
    transport = Transport(player)
    transport.play_album(album_of(one, two, three), one)
    transport.set_repeating(True)
    assert played_out(transport, player, 6) == [1, 2, 3, 1, 2, 3, 1]


def test_repeat_never_settles_on_one_track_of_an_album() -> None:
    """The whole album until it is turned off, not the track it ended on."""
    tracks = tuple(track(number) for number in range(1, 4))
    player = FakePlayer()
    transport = Transport(player)
    transport.play_album(album_of(*tracks), tracks[2])
    transport.set_repeating(True)
    heard = played_out(transport, player, 8)
    assert len(set(heard)) == len(tracks), "every track, not the last one over"


def test_a_repeating_album_is_scattered_afresh_each_time_round() -> None:
    """Otherwise it is one shuffle played on a loop, which is an order.

    Read as one stream cut into times round, because the join belongs to
    neither: an off by one there is a run that looks short when it is not.
    """
    tracks = tuple(track(number) for number in range(1, LONG_ALBUM + 1))
    orders = iter((tuple(reversed(tracks)), tracks))
    player = FakePlayer()
    transport = Transport(player, ordering=lambda _: next(orders))
    transport.play_album(album_of(*tracks), tracks[0])
    transport.set_shuffled(True)
    transport.set_repeating(True)
    stream = played_out(transport, player, LONG_ALBUM * 2 - 1)
    first, second = stream[:LONG_ALBUM], stream[LONG_ALBUM:]
    assert first != second, "a second order was asked for and used"
    assert set(first) == set(second) == set(range(1, LONG_ALBUM + 1))


def test_a_fresh_run_does_not_open_on_the_track_that_just_ended() -> None:
    """Hearing it twice across the join is the one repeat nobody means.

    The order handed back deliberately opens on whatever has just played, so
    the swap is exercised rather than merely available: with a scatter that
    happens not to do it, this passed while the rule did nothing.
    """
    tracks = tuple(track(number) for number in range(1, LONG_ALBUM + 1))
    player = FakePlayer()
    transport = Transport(player)

    def opening_on_what_just_played(given: tuple) -> tuple:
        playing = transport.current
        return (playing, *[one for one in given if one is not playing])

    transport._ordering = opening_on_what_just_played
    transport.play_album(album_of(*tracks), tracks[0])
    transport.set_shuffled(True)
    transport.set_repeating(True)
    heard = played_out(transport, player, LONG_ALBUM)
    ended_on = heard[LONG_ALBUM - 1]
    assert heard[LONG_ALBUM] != ended_on, "the join does not play it twice"
    assert set(heard[:LONG_ALBUM]) == set(range(1, LONG_ALBUM + 1))


def test_one_track_repeating_is_that_track_again() -> None:
    """There is nothing to scatter and no join to avoid."""
    only = track(1)
    player = FakePlayer()
    transport = Transport(player, ordering=reversed_order)
    transport.play_album(album_of(only), only)
    transport.set_shuffled(True)
    transport.set_repeating(True)
    assert played_out(transport, player, 3) == [1, 1, 1, 1]


def test_the_scatter_is_asked_for_once_per_time_round(monkeypatch) -> None:
    """Not once per track: that would be a fresh order under the playhead."""
    tracks = tuple(track(number) for number in range(1, LONG_ALBUM + 1))
    asked: list[int] = []

    def counted(given):
        asked.append(len(given))
        return tuple(reversed(given))

    player = FakePlayer()
    transport = Transport(player, ordering=counted)
    transport.play_album(album_of(*tracks), tracks[0])
    transport.set_shuffled(True)
    transport.set_repeating(True)
    before = len(asked)
    played_out(transport, player, LONG_ALBUM)
    assert len(asked) == before + 1, "one new order for one time round"
    assert asked[-1] == LONG_ALBUM, "and the whole album is what it scattered"
