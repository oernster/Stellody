"""The window's half of pausing for a move of the system's sound output.

Oliver asked on 2026-09-14 that the pause show on the play buttons at once: the
tray at the top and the album pane both wear the face of what a press would do,
so a pause the listener did not make must turn both back to play straight
away rather than at the next poll. The status line says why it happened.
"""

from __future__ import annotations

import pytest
from PySide6.QtCore import QModelIndex
from PySide6.QtWidgets import QApplication
from recording_player import RecordingPlayer
from tray_support import RememberingStore, build, picture

from stellody.ui.album_pane import PAUSE_TOOLTIP, PLAY_TOOLTIP
from stellody.ui.playing import OUTPUT_MOVED_MESSAGE
from stellody.ui.row_text import Column

PLAY_TIP = "Play"
PAUSE_TIP = "Pause"


@pytest.fixture
def window(application: QApplication):
    """A window playing the first track of its one album."""
    player = RecordingPlayer()
    made = build(RememberingStore(), player)
    made._player = player
    album = made._model.index(0, Column.TITLE, QModelIndex())
    made.activate(made._model.index(0, 0, album))
    yield made
    made.close()


class TestAMoveWhileAtrackPlays:
    def test_the_music_is_paused(self, window) -> None:
        window.output_moved()
        assert window._player.calls[-1] == "pause"

    def test_the_top_tray_shows_play_at_once(self, window) -> None:
        button = window._tray.play_button
        assert button.toolTip() == PAUSE_TIP, "playing, so the button pauses"
        pause_face = picture(button)
        window.output_moved()
        assert button.toolTip() == PLAY_TIP
        assert picture(button) != pause_face

    def test_the_album_pane_agrees(self, window) -> None:
        assert window._album_pane.play_button.toolTip() == PAUSE_TOOLTIP
        window.output_moved()
        assert window._album_pane.play_button.toolTip() == PLAY_TOOLTIP

    def test_the_status_line_says_why(self, window) -> None:
        window.output_moved()
        assert window.statusBar().currentMessage() == OUTPUT_MOVED_MESSAGE

    def test_play_carries_on_through_the_new_output(self, window) -> None:
        window.output_moved()
        window._player.calls.clear()
        window.toggle_playback()
        assert window._player.calls == ["load", "play"]
        assert window._tray.play_button.toolTip() == PAUSE_TIP


class TestAMoveWithNothingPlaying:
    def test_nothing_is_said_or_done(self, application: QApplication) -> None:
        player = RecordingPlayer()
        made = build(RememberingStore(), player)
        made.output_moved()
        assert player.calls == []
        assert made.statusBar().currentMessage() == ""
        made.close()
