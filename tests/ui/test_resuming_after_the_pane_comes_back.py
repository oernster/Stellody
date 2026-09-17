"""Rolling the pane up and back down does not send the album back to the top.

Reported by Oliver on 2026-09-17 and reproduced offscreen the same day: play
the third track of an album with the pane open, pause, roll the pane up, roll
it back down, press play. It started the first track instead of carrying on
from the third.

Nothing was wrong with the transport. An album opens with the highlight on its
first track and the play button means the track highlighted in the view on
show, so the pane coming back had quietly thrown away where the listener was.
An album that holds the track in hand now opens on that track.
"""

from __future__ import annotations

from playback_support import album_index, player, track_index, window
from recording_player import RecordingPlayer

from stellody.ui.main_window import MainWindow

__all__ = ["player", "window"]

THIRD = 2
FIRST = 0


def third_track(made: MainWindow):
    """The track the listener was on."""
    return made._model.track_at(track_index(made, THIRD))


class TestPausedWithThePaneRolledUp:
    """Under the sleeves, which is where the pane is the view on show.

    The play button means the track highlighted in the view ON SHOW, so in the
    tree the highlight was never lost and there was nothing to report. Every
    test here therefore turns the sleeves on first.
    """

    def test_play_carries_on_from_where_it_left_off(
        self, window: MainWindow, player: RecordingPlayer
    ) -> None:
        window.show_covers(True)
        window.open_album_at(album_index(window))
        window.activate(track_index(window, THIRD))
        window.toggle_playback()
        assert not window._transport.playing, "paused"
        window.close_album()
        window.open_album_at(album_index(window))
        window.toggle_playback()
        assert window._transport.current is third_track(window)
        assert window._transport.playing

    def test_the_pane_comes_back_pointing_at_the_track_in_hand(
        self, window: MainWindow
    ) -> None:
        window.show_covers(True)
        window.open_album_at(album_index(window))
        window.activate(track_index(window, THIRD))
        window.close_album()
        window.open_album_at(album_index(window))
        assert window._album_pane.current_index().row() == THIRD

    def test_an_album_with_nothing_in_hand_still_opens_on_its_first_track(
        self, window: MainWindow
    ) -> None:
        window.show_covers(True)
        window.open_album_at(album_index(window))
        assert window._album_pane.current_index().row() == FIRST
