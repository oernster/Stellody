"""A track the listener paused must never be read as a track that ended.

Reported against a real library. Pausing a track and pressing play again
started it from its beginning instead of resuming it.

The device cannot tell a hold from an ending: the feeder clears the same flag
for both, so a paused track reports itself exactly as a finished one does.
Acting on that at the next poll, a quarter of a second later, gave the device
back on the last track of a queue, which is what made the press that should
have resumed reload the track from nothing; in the middle of a queue it moved
on to the next track while the listener was still sitting on this one.
"""

from __future__ import annotations

from transport_support import FakePlayer, album_of, track

from stellody.application.transport import Transport
from stellody.domain.playback import PlaybackState


def _paused_on(*tracks):
    """A transport playing the first of these, then paused by the listener."""
    player = FakePlayer()
    transport = Transport(player)
    transport.play_album(album_of(*tracks), tracks[0])
    player.state = PlaybackState.PLAYING
    transport.toggle()
    player.finished = True
    return transport, player


class TestWhileTheListenerIsHolding:
    def test_the_poll_does_nothing(self) -> None:
        """The whole of what this is for."""
        transport, _ = _paused_on(track(1), track(2))
        assert transport.advance_if_finished() is False

    def test_the_device_is_not_given_back(self) -> None:
        """Giving it back is what made the next press reload from nothing."""
        transport, player = _paused_on(track(1))
        transport.advance_if_finished()
        assert "stop" not in player.calls

    def test_pressing_play_resumes_rather_than_reloading(self) -> None:
        """The reported symptom, end to end."""
        transport, player = _paused_on(track(1))
        transport.advance_if_finished()
        transport.toggle()
        assert player.calls.count("load") == 1, player.calls

    def test_the_queue_stays_where_the_listener_left_it(self) -> None:
        """In the middle of an album it used to move on unasked."""
        one, two = track(1), track(2)
        transport, _ = _paused_on(one, two)
        transport.advance_if_finished()
        assert transport.current is one


class TestATrackThatReallyEnds:
    def test_it_still_moves_on(self) -> None:
        """The hold must not swallow an ending nobody asked for."""
        player = FakePlayer()
        transport = Transport(player)
        one, two = track(1), track(2)
        transport.play_album(album_of(one, two), one)
        player.finished = True
        assert transport.advance_if_finished() is True
        assert transport.current is two

    def test_an_ending_after_a_resume_still_moves_on(self) -> None:
        """Resuming puts the hold back, else one pause would deafen the poll."""
        one, two = track(1), track(2)
        transport, player = _paused_on(one, two)
        player.state = PlaybackState.PAUSED
        transport.toggle()
        player.finished = True
        assert transport.advance_if_finished() is True
        assert transport.current is two
