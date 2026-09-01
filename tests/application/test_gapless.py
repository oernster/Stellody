"""Lining the next track up, plus the queue catching up when it is run into.

A gapless transition happens inside the engine, with nothing asked and nothing
loaded: the feeder thread simply reads on. So there are two halves to check
here. The transport must say what follows EARLY, while the current track is
still playing, since anything decided at the seam is already too late. Then,
when the device reports it has crossed one, the queue must land where the music
actually went rather than where the rules would send it now.

The device is the hand written stand-in the other transport tests use. Its
`cross` is what the feeder thread does on its own thread in the real engine.
"""

from __future__ import annotations

from transport_support import FakePlayer, album_of, reversed_order, track

from stellody.application.transport import Transport
from stellody.domain.album import Album
from stellody.domain.playback import RepeatMode
from stellody.domain.track import Track


def _playing(*tracks: Track) -> tuple[Transport, FakePlayer, Album]:
    """A transport playing the first of these tracks, plus its device."""
    player = FakePlayer()
    transport = Transport(player, ordering=reversed_order)
    album = album_of(*tracks)
    transport.play_album(album, tracks[0])
    return transport, player, album


def test_the_next_track_is_lined_up_while_this_one_is_still_playing() -> None:
    """Anything decided at the seam is already too late to decode."""
    first, second = track(1), track(2)
    _, player, _ = _playing(first, second)
    assert player.lined_up[-1] == second.source


def test_holding_one_track_lines_that_same_track_up() -> None:
    """Repeat one has to be seamless too, which is the whole point of it."""
    first, second = track(1), track(2)
    transport, player, _ = _playing(first, second)
    transport.set_repeat(RepeatMode.ONE)
    assert player.lined_up[-1] == first.source


def test_the_end_of_an_album_lines_nothing_up_when_repeat_is_off() -> None:
    """There is nothing to run into, so the device is told so rather than left."""
    first, second = track(1), track(2)
    transport, player, _ = _playing(first, second)
    transport.next()
    assert player.lined_up[-1] is None


def test_the_end_of_a_repeating_album_lines_up_its_first_track() -> None:
    """The wrap is knowable in advance, so that seam can be closed."""
    first, second = track(1), track(2)
    transport, player, _ = _playing(first, second)
    transport.set_repeat(RepeatMode.ALBUM)
    transport.next()
    assert player.lined_up[-1] == first.source


def test_a_scattered_album_about_to_wrap_lines_nothing_up() -> None:
    """Its next order is chosen as it begins again, so there is nothing to name.

    Deliberately gapped rather than guessed at: lining up the wrong track would
    be worse than the seam it saved.
    """
    first, second = track(1), track(2)
    transport, player, _ = _playing(first, second)
    transport.set_repeat(RepeatMode.ALBUM)
    transport.set_shuffled(True)
    while transport.queue.has_next:
        transport.next()
    assert player.lined_up[-1] is None


def test_changing_repeat_relines_what_follows() -> None:
    """The switch can move after a track is lined up and before it is reached."""
    first, second = track(1), track(2)
    transport, player, _ = _playing(first, second)
    assert player.lined_up[-1] == second.source
    transport.set_repeat(RepeatMode.ONE)
    assert player.lined_up[-1] == first.source


def test_crossing_a_seam_moves_the_queue_without_loading_anything() -> None:
    """The music is already there; loading would restart what is playing."""
    first, second = track(1), track(2)
    transport, player, _ = _playing(first, second)
    loads = player.calls.count("load")
    player.cross()

    assert transport.advance_if_finished() is True
    assert transport.current is second
    assert player.calls.count("load") == loads, "nothing was opened at the seam"


def test_a_crossed_track_is_counted_as_a_play() -> None:
    """It reached its end, which is the whole of what counts as a play."""
    first, second = track(1), track(2)
    transport, player, album = _playing(first, second)
    played: list[tuple[Album, Track]] = []
    transport.report_plays_to(lambda a, t: played.append((a, t)))
    player.cross()
    transport.advance_if_finished()
    assert played == [(album, first)]


def test_crossing_lines_up_whatever_follows_the_new_track() -> None:
    """One seam closed has to leave the next one closed as well."""
    first, second, third = track(1), track(2), track(3)
    transport, player, _ = _playing(first, second, third)
    player.cross()
    transport.advance_if_finished()
    assert player.lined_up[-1] == third.source


def test_a_seam_is_reported_once_however_often_it_is_asked_about() -> None:
    """The count is polled, so asking twice must not advance twice."""
    first, second, third = track(1), track(2), track(3)
    transport, player, _ = _playing(first, second, third)
    player.cross()
    assert transport.advance_if_finished() is True
    assert transport.advance_if_finished() is False
    assert transport.current is second


def test_a_stopped_device_is_not_read_as_having_crossed() -> None:
    """Stopping drops the count with the session, which must not read as a move."""
    first, second = track(1), track(2)
    transport, player, _ = _playing(first, second)
    player.cross()
    transport.advance_if_finished()
    transport.stop()
    player.crossings = 0

    assert transport.advance_if_finished() is False
    assert transport.current is second
