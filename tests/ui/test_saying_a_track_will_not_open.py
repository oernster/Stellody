"""What the window says when the track it was asked to play will not open.

The application layer reports the failure; the window is what a listener
actually reads. These assert the two things that were wrong. The message saying why must
survive the press that caused it. The device must be given back rather than
left open behind a track that never started.
"""

from __future__ import annotations

import pytest
from conftest import RecordingPlayer
from PySide6.QtWidgets import QApplication
from test_playing import BareStore, album, track_index

from stellody.application.scan import LoadLibrary, ScanLibrary
from stellody.application.transport import Transport
from stellody.domain.playback import PlaybackError
from stellody.ui.main_window import MainWindow

REASON = "the decoder for this format is not installed"
SECOND_TRACK = 1


class RefusingPlayer(RecordingPlayer):
    """A device that will not open the track it is given."""

    def load(self, source, request):
        """Refuse, as the real one does when a file cannot be opened."""
        self.calls.append("load")
        raise PlaybackError(REASON)


@pytest.fixture
def window(application: QApplication) -> MainWindow:
    """A real window over a device that refuses everything, showing one album."""
    store = BareStore()
    player = RefusingPlayer()

    def session():
        return ScanLibrary(None, None, None, store), store

    made = MainWindow(
        scan_session=session,
        loader=LoadLibrary(store),
        transport=Transport(player),
        settings=store,
    )
    made._player = player
    made._model.set_albums((album(),))
    return made


class TestActivatingATrackThatWillNotOpen:
    def test_the_listener_is_told_why(self, window: MainWindow) -> None:
        """The whole of what this is for."""
        window.activate(track_index(window, SECOND_TRACK))
        assert REASON in window.statusBar().currentMessage()

    def test_the_window_does_not_claim_it_is_playing(self, window: MainWindow) -> None:
        """The reason used to be overwritten by "Playing" in the same press.

        The transport reported the failure and did not raise, so the window
        read the press as a success, said the track was playing and buried the
        one message that said it was not.
        """
        window.activate(track_index(window, SECOND_TRACK))
        assert "Playing" not in window.statusBar().currentMessage()

    def test_the_device_is_given_back(self, window: MainWindow) -> None:
        """A track that never started must not leave a device held open."""
        window.activate(track_index(window, SECOND_TRACK))
        assert "stop" in window._player.calls
