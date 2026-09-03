"""The two play buttons must answer a press the same way.

Reported against a real library: pausing a track and pressing play again
started it from its beginning. The tray's button resumed; the one on the album
pane started the open album from its first track, which is a reload rather than
a resume and looks exactly like the track beginning again.

One press, one meaning. Where a track is loaded the pane's button now answers
exactly as the tray's does; where nothing is loaded at all it still starts the
album it is attached to, which is the only thing it could sensibly mean there.
"""

from __future__ import annotations

import pytest
from conftest import RecordingPlayer
from PySide6.QtCore import QModelIndex
from PySide6.QtWidgets import QApplication
from tray_support import RememberingStore, build

from stellody.domain.playback import PlaybackState
from stellody.ui.row_text import Column

SECOND_TRACK = 1


@pytest.fixture
def window(application: QApplication):
    """A window on the sleeves with its one album open underneath."""
    player = RecordingPlayer()
    made = build(RememberingStore(), player)
    made._player = player
    made.toggle_view()
    made.open_album_at(made._model.index(0, Column.TITLE, QModelIndex()))
    yield made
    made.close()


def _playing_the_second_track(window) -> None:
    """Start the second track, so a restart from the first is visible."""
    album = window._model.index(0, Column.TITLE, QModelIndex())
    window.activate(window._model.index(SECOND_TRACK, 0, album))
    window._player.state = PlaybackState.PLAYING


class TestPressingPlayAfterAPause:
    def test_the_pane_button_resumes_rather_than_reloading(self, window) -> None:
        """The whole of what this is for."""
        _playing_the_second_track(window)
        window.play_shown_album()
        window._player.state = PlaybackState.PAUSED
        window.play_shown_album()
        assert window._player.calls.count("load") == 1, window._player.calls

    def test_the_pane_button_stays_on_the_track(self, window) -> None:
        """It used to go back to the first track of the album."""
        _playing_the_second_track(window)
        held = window._transport.current
        window.play_shown_album()
        window._player.state = PlaybackState.PAUSED
        window.play_shown_album()
        assert window._transport.current is held

    def test_both_buttons_answer_alike(self, window) -> None:
        """The reported difference, stated as the rule it broke."""
        _playing_the_second_track(window)
        window.toggle_playback()
        window._player.state = PlaybackState.PAUSED
        window.toggle_playback()
        from_the_tray = list(window._player.calls)
        window._player.calls.clear()

        _playing_the_second_track(window)
        window.play_shown_album()
        window._player.state = PlaybackState.PAUSED
        window.play_shown_album()
        assert window._player.calls == from_the_tray


class TestWhatEachButtonStillDoes:
    def test_the_pane_button_pauses_what_is_playing(self, window) -> None:
        """A press on a pause face asks to stop, not to go somewhere else."""
        _playing_the_second_track(window)
        window.play_shown_album()
        assert window._player.calls[-1] == "pause"

    def test_the_pane_button_starts_the_open_album_from_nothing(self, window) -> None:
        """With nothing loaded it is the only thing the button could mean."""
        window.play_shown_album()
        assert window._player.calls == ["load", "play"]
        assert window._transport.current.track_number == 1
