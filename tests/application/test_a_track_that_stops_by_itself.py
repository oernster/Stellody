"""A track whose feeder fails is named with the reason; the queue moves on.

Found by the audit of 2026-10-03: a feeder that died left the window saying the
track was playing, with the position frozen and the queue stalled. The engine
now keeps the reason and holds the track (`PlaybackPort.failure`). This is the
transport's half: at the next poll the track is named with that reason for the
window to say, then the queue carries on past it as it would at an ending.
"""

from __future__ import annotations

from recording_player import RecordingPlayer
from transport_support import album_of, track

from stellody.application.transport import Transport
from stellody.domain.playback import PlaybackState, RepeatMode

REASON = "number of channels must match"


def test_a_failure_names_the_track_and_moves_on() -> None:
    """Said once, with the reason; the next track opens and plays."""
    one, two = track(1), track(2)
    player = RecordingPlayer()
    transport = Transport(player)
    transport.play_album(album_of(one, two), one)
    player.failure = REASON
    player.calls.clear()

    assert transport.advance_if_finished() is True
    failure = transport.take_failure()
    assert failure is not None
    assert (failure.track, failure.reason) == (one, REASON)
    assert transport.take_failure() is None, "said once, not at every poll"
    assert transport.current == two
    assert player.calls[-2:] == ["load", "play"]
    assert player.state is PlaybackState.PLAYING


def test_a_failure_on_the_last_track_gives_the_device_back() -> None:
    """Nothing to move on to: the device is released and the track named."""
    one = track(1)
    player = RecordingPlayer()
    transport = Transport(player)
    transport.play_album(album_of(one), one)
    player.failure = REASON
    player.calls.clear()

    assert transport.advance_if_finished() is True
    assert player.calls == ["stop"]
    failure = transport.take_failure()
    assert failure is not None
    assert failure.track == one


def test_a_failure_is_not_counted_as_a_play() -> None:
    """A track that stopped by itself did not play out."""
    one, two = track(1), track(2)
    played: list[str] = []
    player = RecordingPlayer()
    transport = Transport(player, played=lambda _album, done: played.append(done.title))
    transport.play_album(album_of(one, two), one)
    player.failure = REASON

    transport.advance_if_finished()
    assert played == []


def test_a_failure_moves_on_even_while_one_track_repeats() -> None:
    """Repeating the track that failed would fail again at every poll."""
    one, two = track(1), track(2)
    player = RecordingPlayer()
    transport = Transport(player)
    transport.set_repeat(RepeatMode.ONE)
    transport.play_album(album_of(one, two), one)
    player.failure = REASON

    transport.advance_if_finished()
    assert transport.current == two


def test_nothing_is_said_while_nothing_has_failed() -> None:
    """No failure, no message."""
    one, two = track(1), track(2)
    player = RecordingPlayer()
    transport = Transport(player)
    transport.play_album(album_of(one, two), one)
    assert transport.advance_if_finished() is False
    assert transport.take_failure() is None
