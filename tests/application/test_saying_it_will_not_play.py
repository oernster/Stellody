"""A track that will not open stops the transport rather than passing quietly.

Found on a real machine. A checkout whose requirements had not been installed
had no decoder for M4A, so opening one raised inside the slot that asked for
it, the exception left the transport entirely and the window did nothing
whatever: no message, no movement, no error. A listener cannot tell that from a
press that missed the button.

The same shape reaches every other way a track can fail to open, which are
ordinary rather than exotic: a drive unplugged since the last scan, a file
renamed underneath the library, a device another program has taken exclusively.

The transport caught all of them for a while and reported through a callback.
That was wrong: the caller then read the press as a success, so it left the
device open and said the track was playing over the top of the message saying
it would not. The failure is raised instead; the caller that has to give the
device back is the one that hears about it.
"""

from __future__ import annotations

import pytest
from transport_support import FakePlayer, album_of, track

from stellody.application.transport import Transport
from stellody.domain.playback import PlaybackError

REASON = "the decoder for this format is not installed"


class RefusingPlayer(FakePlayer):
    """A device that will not open the track it is given."""

    def load(self, source, request):
        """Refuse, as the real one does when a file cannot be opened."""
        self.calls.append("load")
        raise PlaybackError(REASON)


class TestATrackThatWillNotOpen:
    def test_the_failure_reaches_the_caller(self) -> None:
        """The whole of what this is for."""
        transport = Transport(RefusingPlayer())
        one = track(1)
        with pytest.raises(PlaybackError):
            transport.play_album(album_of(one, track(2)), one)

    def test_the_reason_is_carried_whole(self) -> None:
        """A reason naming the cause is what a listener can act on."""
        transport = Transport(RefusingPlayer())
        one = track(1)
        with pytest.raises(PlaybackError, match=REASON):
            transport.play_album(album_of(one), one)

    def test_the_track_that_failed_can_still_be_named(self) -> None:
        """The caller says which track it was, so the queue must survive."""
        transport = Transport(RefusingPlayer())
        wanted = track(1)
        with pytest.raises(PlaybackError):
            transport.play_album(album_of(wanted, track(2)), wanted)
        assert transport.current == wanted

    def test_nothing_is_asked_to_play(self) -> None:
        """Playing a device that never opened would be the next fault along."""
        player = RefusingPlayer()
        transport = Transport(player)
        one = track(1)
        with pytest.raises(PlaybackError):
            transport.play_album(album_of(one), one)
        assert "play" not in player.calls


class TestATrackThatOpensNormally:
    def test_the_quiet_path_stays_quiet(self) -> None:
        """Nothing raises and the device is asked to play."""
        player = FakePlayer()
        transport = Transport(player)
        first = track(1)
        transport.play_album(album_of(first), first)
        assert "play" in player.calls
