"""A track that will not open is said out loud, never left as silence.

Found on a real machine. A checkout whose requirements had not been installed
had no decoder for M4A, so opening one raised inside the slot that asked for
it, the exception left the transport entirely and the window did nothing
whatever: no message, no movement, no error. A listener cannot tell that from a
press that missed the button.

The same shape reaches every other way a track can fail to open, which are
ordinary rather than exotic: a drive unplugged since the last scan, a file
renamed underneath the library, a device another program has taken exclusively.
All of them arrive as one thing to a listener, so all of them are reported the
same way and none of them takes the transport down.
"""

from __future__ import annotations

from transport_support import FakePlayer, album_of, track

from stellody.application.transport import Transport
from stellody.domain.playback import PlaybackError
from stellody.domain.track import Track

REASON = "the decoder for this format is not installed"


class RefusingPlayer(FakePlayer):
    """A device that will not open the track it is given."""

    def load(self, source, request):
        """Refuse, as the real one does when a file cannot be opened."""
        self.calls.append("load")
        raise PlaybackError(REASON)


def _transport() -> tuple[Transport, list[tuple[Track, str]], RefusingPlayer]:
    """A transport over a device that refuses, with the failures collected."""
    player = RefusingPlayer()
    transport = Transport(player)
    said: list[tuple[Track, str]] = []
    transport.report_failures_to(lambda one, reason: said.append((one, reason)))
    return transport, said, player


class TestATrackThatWillNotOpen:
    def test_the_listener_is_told(self) -> None:
        """The whole of what this is for."""
        transport, said, _ = _transport()
        one = track(1)
        transport.play_album(album_of(one, track(2)), one)
        assert said, "a track that would not open must not pass in silence"

    def test_the_reason_is_carried_whole(self) -> None:
        """A reason naming the cause is what a listener can act on."""
        transport, said, _ = _transport()
        one = track(1)
        transport.play_album(album_of(one), one)
        assert REASON in said[0][1]

    def test_the_track_is_named(self) -> None:
        """Which track failed, so the message can say it."""
        transport, said, _ = _transport()
        wanted = track(1)
        transport.play_album(album_of(wanted, track(2)), wanted)
        assert said[0][0] == wanted

    def test_the_failure_does_not_escape_the_transport(self) -> None:
        """It used to, which is how it reached the window as nothing at all."""
        transport, _, _ = _transport()
        one = track(1)
        transport.play_album(album_of(one), one)

    def test_nothing_is_asked_to_play(self) -> None:
        """Playing a device that never opened would be the next fault along."""
        transport, _, player = _transport()
        one = track(1)
        transport.play_album(album_of(one), one)
        assert "play" not in player.calls


class TestWhenNobodyIsListening:
    def test_a_transport_told_nobody_still_does_not_raise(self) -> None:
        """The reporting is optional; surviving the failure is not."""
        transport = Transport(RefusingPlayer())
        one = track(1)
        transport.play_album(album_of(one), one)


class TestATrackThatOpensNormally:
    def test_nothing_is_reported(self) -> None:
        """The quiet path stays quiet."""
        player = FakePlayer()
        transport = Transport(player)
        said: list[tuple[Track, str]] = []
        transport.report_failures_to(lambda one, reason: said.append((one, reason)))
        first = track(1)
        transport.play_album(album_of(first), first)
        assert said == []
        assert "play" in player.calls
