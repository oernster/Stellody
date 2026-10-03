"""A track that stopped by itself is named on the status line, with the reason.

The window's half of the audit finding of 2026-10-03: the engine keeps why its
feeder failed and the transport moves the queue on past the track. The poll is
what says so, in the words a track that will not open is given, since to a
listener the two are the same thing: this song is not playing; here is why.
"""

from __future__ import annotations

from playback_support import album, player, window
from recording_player import RecordingPlayer

from stellody.domain.playback import PlaybackState
from stellody.ui.playing import unplayable_words

__all__ = ["player", "window"]

REASON = "number of channels must match"


def test_the_poll_names_the_track_that_stopped_and_plays_on(
    window, player: RecordingPlayer
) -> None:
    """Said with the track and the reason; the next track is playing."""
    held = album()
    first, second = held.ordered_tracks()[:2]
    window._transport.play_album(held, first)
    player.failure = REASON
    window._poll_transport()
    said = window.statusBar().currentMessage()
    assert said == unplayable_words(first, REASON)
    assert first.title in said
    assert REASON in said
    assert window._transport.current == second
    assert player.state is PlaybackState.PLAYING


def test_words_for_a_failure_with_no_track_still_give_the_reason() -> None:
    """Nothing in hand to name: the reason is said all the same."""
    assert REASON in unplayable_words(None, REASON)
