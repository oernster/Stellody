"""The playing row stays marked across a library built afresh underneath it.

Reported by Oliver on 2026-09-17 with a screenshot and reproduced offscreen
the same day: the foot named the playing track while no row anywhere carried
the mark. He suspected the album pane being rolled up and back down; that was
measured and is not it, the pane restores the mark perfectly.

What does it is a reload. A scan, a repair from the health report and a tag
edit all rebuild every album and every track, while the transport plays on
with the track object it was handed. A mark held by that object then belongs
to a track with no row anywhere, so nothing is painted and nothing complains.

The handle is what survives a rebuild, which is why the listening log has
always used one; see `stellody.domain.listening`.
"""

from __future__ import annotations

from playback_support import POLLS, album, player, track_index, window
from PySide6.QtCore import Qt
from recording_player import RecordingPlayer

from stellody.ui.main_window import MainWindow

__all__ = ["player", "window"]

PLAYING_ROW = 1
TRACK_COUNT = 3


def marked_rows(made: MainWindow) -> list[int]:
    """Every track row the model paints the playing colour."""
    return [
        row
        for row in range(TRACK_COUNT)
        if track_index(made, row).data(Qt.ItemDataRole.BackgroundRole) is not None
    ]


def start_playing(made: MainWindow) -> None:
    """Play the middle track, then let the transport poll say so."""
    made.activate(track_index(made, PLAYING_ROW))
    for _ in range(POLLS):
        made._poll_transport()


class TestAReloadUnderAPlayingTrack:
    def test_the_mark_is_on_the_playing_row_to_begin_with(
        self, window: MainWindow
    ) -> None:
        start_playing(window)
        assert marked_rows(window) == [PLAYING_ROW]

    def test_the_mark_survives_the_library_being_rebuilt(
        self, window: MainWindow
    ) -> None:
        """The library that comes back is equal in every way and new in every object."""
        start_playing(window)
        window.show_library((album(),), ())
        for _ in range(POLLS):
            window._poll_transport()
        assert marked_rows(window) == [PLAYING_ROW]

    def test_the_highlight_still_follows_a_track_change(
        self, window: MainWindow
    ) -> None:
        """Finding the row again is what the follow needs as well as the mark.

        The transport plays the album it was handed, so Next gives a track
        from before the reload: the row it belongs to has to be found by
        handle or the highlight is left behind on the track that ended.
        """
        start_playing(window)
        window.show_library((album(),), ())
        window.next_track()
        for _ in range(POLLS):
            window._poll_transport()
        assert window._tree.currentIndex().row() == PLAYING_ROW + 1
        assert marked_rows(window) == [PLAYING_ROW + 1]

    def test_the_listener_is_still_left_alone_after_a_reload(
        self, window: MainWindow
    ) -> None:
        """Moving the highlight by hand keeps it, which is the older rule."""
        start_playing(window)
        window.show_library((album(),), ())
        window._tree.setCurrentIndex(track_index(window, 0))
        for _ in range(POLLS):
            window._poll_transport()
        assert window._tree.currentIndex().row() == 0

    def test_a_reload_with_nothing_playing_marks_nothing(
        self, window: MainWindow, player: RecordingPlayer
    ) -> None:
        window.show_library((album(),), ())
        for _ in range(POLLS):
            window._poll_transport()
        assert marked_rows(window) == []
