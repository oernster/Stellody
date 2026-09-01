"""The album open under the sleeves highlights whatever is playing too.

The grid keeps its own highlight, in the album opened beneath it, so pointing
the library tree at a track left the visible one where it was. Reported from
the built application against an album playing through: the music ran on into
the next track while nothing on screen said which one.

It predates gapless playback, which only made it happen at every join rather
than at the end of a track, so both ways in are held here.
"""

from __future__ import annotations

from conftest import RecordingPlayer
from playback_support import album_index, player, track_index, window

from stellody.ui.main_window import MainWindow

__all__ = ["album_index", "player", "track_index", "window"]


def test_a_crossing_carries_the_highlight_in_the_covers_view(
    window: MainWindow, player: RecordingPlayer
) -> None:
    """The open album under the sleeves holds its own highlight, not the tree's.

    Reported from the built application against an album playing through: the
    music ran on into the next track while the highlight stayed where it was,
    leaving nothing on screen saying what was playing.
    """
    window.toggle_view()
    window.open_album_at(album_index(window))
    window.activate(track_index(window, 0))
    player.cross()
    window._poll_transport()

    assert window._transport.current.title == "Track 2"
    playing = window._model.track_at(window.highlighted())
    assert playing is window._transport.current


def test_a_track_playing_out_carries_the_highlight_in_the_covers_view(
    window: MainWindow, player: RecordingPlayer
) -> None:
    """The same fault, reached the older way round, so it cannot come back.

    This one predates gapless playback: pointing the tree at a track has never
    moved the highlight the grid shows. Gapless only made it happen at every
    join rather than at the end of a track.
    """
    window.toggle_view()
    window.open_album_at(album_index(window))
    window.activate(track_index(window, 0))
    player.finished = True
    window._poll_transport()

    assert window._transport.current.title == "Track 2"
    assert window._model.track_at(window.highlighted()) is window._transport.current


def test_the_pane_refuses_a_track_of_an_album_it_is_not_showing(
    window: MainWindow,
) -> None:
    """Otherwise it reports a highlight it never actually placed."""
    window.toggle_view()
    window.open_album_at(album_index(window))
    assert window._album_pane.show_track(album_index(window)) is False
