"""Stepping back off a video hands the library area straight back.

Back lands on a track's beginning and waits there rather than playing on, so a
run of videos stepped through backwards is a run of tracks nobody has started.
Holding the library area for those meant showing their first frame; a music
video's first frame is black: measured at 0.0 mean brightness through the whole
first fifth of a second on both files in the album this was found on. So the
window went black and stayed black, on a track that was not playing.

What settles it is not the colour of the frame. A listener who has not started
a track is still looking for one; the library is what they are looking
through. A track paused PART WAY through is the opposite case and keeps its
picture, because that one has been started and is waiting to go on.
"""

from __future__ import annotations

import pytest
from conftest import RecordingPlayer
from picture_support import make_window, reached, track_index
from PySide6.QtWidgets import QApplication


@pytest.fixture
def player() -> RecordingPlayer:
    return RecordingPlayer()


@pytest.fixture
def window(application: QApplication, player: RecordingPlayer):
    """A window with a picture service over the fake port."""
    return make_window(application, player)


def showing_the_picture(window) -> bool:
    """Whether the picture has the library's area."""
    return window._library.currentWidget() is window.picture_surface


class TestATrackWaitingAtItsStart:
    def test_back_off_a_video_gives_the_library_area_back(self, window, player):
        window.activate(track_index(window, 1))
        reached(player, 1234)
        window._poll_transport()
        assert showing_the_picture(window)

        window.previous_track()
        window._poll_transport()
        assert not showing_the_picture(window)

    def test_it_leaves_nothing_of_the_video_behind(self, window, player):
        window.activate(track_index(window, 1))
        reached(player, 1234)
        window._poll_transport()
        window._tick_picture()
        assert window.picture_surface.has_picture

        window.previous_track()
        window._poll_transport()
        assert not window.picture_surface.has_picture

    def test_the_file_is_given_back_too(self, window, player):
        """Nothing is held open for a track sitting unplayed."""
        window.activate(track_index(window, 1))
        window._poll_transport()
        opened = window._pictures._reader
        window.previous_track()
        window._poll_transport()
        assert opened.closed
        assert not window._pictures.showing

    def test_the_window_comes_back_with_it(self, window, player):
        """A video filling the window does not leave a bare library behind."""
        window.activate(track_index(window, 1))
        reached(player, 1234)
        window._poll_transport()
        window._tick_picture()
        window.fill_window_with_picture()
        assert not window._tray.isVisible()

        window.previous_track()
        window._poll_transport()
        assert not window.picture_fills_window
        assert window._tray.isVisible()

    def test_playing_it_takes_the_area_again(self, window, player):
        """The picture is not given up for good, only while nobody asked."""
        window.activate(track_index(window, 1))
        reached(player, 1234)
        window._poll_transport()
        window.previous_track()
        window._poll_transport()
        assert not showing_the_picture(window)

        window.toggle_playback()
        window._poll_transport()
        assert showing_the_picture(window)


class TestATrackPausedPartWayThrough:
    def test_pausing_a_video_keeps_its_picture(self, window, player):
        """Pause is not Back: that track was started and is waiting to go on."""
        window.activate(track_index(window, 1))
        reached(player, 1234)
        window._poll_transport()
        assert showing_the_picture(window)

        window.toggle_playback()
        window._poll_transport()
        assert not window._transport.playing
        assert showing_the_picture(window)
