"""Pausing means paused, whatever is pressed next.

Reported from use. Pause an album, then press Next: it started playing.
Nothing had asked it to. Skipping while paused is an ordinary thing to do,
looking for the track you actually want before letting it go, while the pause
button had just been pressed: the one thing the listener had said was that
they wanted silence.

The awkward half is that the same door is used by the device reaching the end
of a track, where playing on is exactly right. Those are two different
questions asked through one method: a listener overruling the queue, plus a
track simply ending. Only the first of them may be quiet; a fix that
confused them would stop the music at every track boundary instead.
"""

from __future__ import annotations

from transport_support import FakePlayer, album_of, track

from stellody.application.transport import Transport
from stellody.domain.moving import RepeatMode
from stellody.domain.playback import PlaybackState


def _paused_on_the_first_of_three() -> tuple[Transport, FakePlayer]:
    """An album playing, then paused on its first track."""
    player = FakePlayer()
    transport = Transport(player)
    one, two, three = track(1), track(2), track(3)
    transport.play_album(album_of(one, two, three), one)
    transport.toggle()
    assert transport.state is PlaybackState.PAUSED, "the fixture must start paused"
    player.calls.clear()
    return transport, player


class TestSkippingWhilePaused:
    def test_next_does_not_start_playing(self) -> None:
        """The whole of what was reported."""
        transport, player = _paused_on_the_first_of_three()
        transport.next()
        assert "play" not in player.calls

    def test_it_still_moves_to_the_next_track(self) -> None:
        """Staying paused is not the same as refusing to move."""
        transport, _ = _paused_on_the_first_of_three()
        transport.next()
        assert transport.current == track(2)

    def test_the_track_is_opened_and_waiting(self) -> None:
        """Opened so it starts instantly, waiting so it starts when asked."""
        transport, player = _paused_on_the_first_of_three()
        transport.next()
        assert "load" in player.calls
        assert transport.state is PlaybackState.PAUSED

    def test_skipping_twice_stays_paused(self) -> None:
        transport, player = _paused_on_the_first_of_three()
        transport.next()
        transport.next()
        assert "play" not in player.calls
        assert transport.current == track(3)

    def test_it_plays_when_asked_afterwards(self) -> None:
        """The listener keeps the moment to carry on."""
        transport, player = _paused_on_the_first_of_three()
        transport.next()
        transport.toggle()
        assert "play" in player.calls
        assert transport.state is PlaybackState.PLAYING


class TestSkippingWhilePlaying:
    def test_next_keeps_playing(self) -> None:
        """The other half of the rule, which must not have been traded away."""
        player = FakePlayer()
        transport = Transport(player)
        one, two = track(1), track(2)
        transport.play_album(album_of(one, two), one)
        assert transport.state is PlaybackState.PLAYING
        player.calls.clear()
        transport.next()
        assert "play" in player.calls
        assert transport.current == two


class TestATrackEndingOfItsOwnAccord:
    """The same door, the other question. An ending plays on regardless."""

    def _finished_on_the_first_of_two(self) -> tuple[Transport, FakePlayer]:
        player = FakePlayer()
        transport = Transport(player)
        one, two = track(1), track(2)
        transport.play_album(album_of(one, two), one)
        player.finished = True
        player.state = PlaybackState.PAUSED
        player.calls.clear()
        return transport, player

    def test_the_music_carries_on(self) -> None:
        """A device that has run out is not a listener asking for silence.

        This is the regression a careless fix would cause: the player reports
        PAUSED once a track has played out, so reading that as "the listener
        paused" would stop the album dead at every track boundary.
        """
        transport, player = self._finished_on_the_first_of_two()
        assert transport.advance_if_finished() is True
        assert "play" in player.calls

    def test_it_moved_on(self) -> None:
        transport, _ = self._finished_on_the_first_of_two()
        transport.advance_if_finished()
        assert transport.current == track(2)

    def test_holding_one_track_still_replays_it(self) -> None:
        transport, player = self._finished_on_the_first_of_two()
        transport.set_repeat(RepeatMode.ONE)
        player.calls.clear()
        assert transport.advance_if_finished() is True
        assert "play" in player.calls
        assert transport.current == track(1)
