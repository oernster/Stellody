"""A video track takes the library's own area, then hands it straight back.

The point of taking the area rather than opening a window over it is that a
bonus video is a track like the song beside it on the same disc: it plays where
the library was, then when it is done the listener is back exactly where they
were, on the view they were on, scrolled where they had scrolled to.

Driven through a hand-written picture port. What a real one decodes is settled
in the infrastructure suite against real encoded files; what is settled here is
where the picture goes and when it leaves.
"""

from __future__ import annotations

import pytest
from conftest import RecordingPlayer
from picture_support import (  # noqa: F401
    HEIGHT,
    WIDTH,
    a_picture,
    album,
    make_window,
    reached,
    track_index,
)
from playback_support import BareStore
from PySide6.QtWidgets import QApplication

from stellody.application.scan import LoadLibrary, ScanLibrary
from stellody.application.transport import Transport
from stellody.domain.picture import Picture


@pytest.fixture
def player() -> RecordingPlayer:
    return RecordingPlayer()


@pytest.fixture
def window(application: QApplication, player: RecordingPlayer):
    """A window with a picture service over the fake port."""
    return make_window(application, player)


class TestTakingTheArea:
    def test_a_song_shows_no_picture(self, window, application) -> None:
        window.activate(track_index(window, 0))
        window._poll_transport()
        assert window._library.currentWidget() is not window.picture_surface

    def test_a_video_track_takes_the_library_area(self, window) -> None:
        window.activate(track_index(window, 1))
        window._poll_transport()
        assert window._library.currentWidget() is window.picture_surface

    def test_the_picture_shows_the_moment_the_sound_has_reached(
        self, window, player
    ) -> None:
        """The sound is the clock: the tick asks it rather than counting."""
        window.activate(track_index(window, 1))
        reached(player, 1234)
        window._poll_transport()
        window._tick_picture()
        assert window.picture_surface.has_picture

    def test_the_surface_keeps_the_shape_of_the_picture(self, window, player) -> None:
        """A frame is not stretched to the window it happens to be in."""
        window.activate(track_index(window, 1))
        reached(player, 500)
        window._poll_transport()
        window._tick_picture()
        drawn = window.picture_surface.picture_rect()
        assert drawn.width() == drawn.height()
        assert drawn.width() <= window.picture_surface.width()
        assert drawn.height() <= window.picture_surface.height()


class TestGivingItBack:
    def test_moving_to_a_song_puts_the_library_back(self, window) -> None:
        window.activate(track_index(window, 1))
        window._poll_transport()
        window.activate(track_index(window, 0))
        window._poll_transport()
        assert window._library.currentWidget() is not window.picture_surface

    def test_the_view_that_was_on_is_the_view_that_comes_back(
        self, window, application
    ) -> None:
        """The sleeves, if that is where the listener was."""
        window.toggle_view()
        application.processEvents()
        assert window.showing_covers
        window.activate(track_index(window, 1))
        window._poll_transport()
        assert window._library.currentWidget() is window.picture_surface
        window.activate(track_index(window, 0))
        window._poll_transport()
        assert window.showing_covers

    def test_nothing_of_one_track_is_left_over_another(self, window, player) -> None:
        window.activate(track_index(window, 1))
        reached(player, 500)
        window._poll_transport()
        window._tick_picture()
        window.activate(track_index(window, 0))
        window._poll_transport()
        assert window.picture_surface.has_picture is False


class TestAWindowWithoutTheService:
    def test_it_shows_no_picture_and_says_nothing(
        self, application: QApplication, player: RecordingPlayer
    ) -> None:
        """Every test about something else builds one of these."""
        from stellody.ui.main_window import MainWindow

        store = BareStore()

        def session():
            return ScanLibrary(None, None, None, store), store

        made = MainWindow(
            scan_session=session,
            loader=LoadLibrary(store),
            transport=Transport(player),
            settings=store,
        )
        made._model.set_albums((album(),))
        made.show()
        made.activate(track_index(made, 1))
        made._poll_transport()
        made._tick_picture()
        assert made.picture_surface.has_picture is False
        assert made._library.currentWidget() is not made.picture_surface


class TestFillingTheWindow:
    def test_it_starts_at_the_library_size(self, window) -> None:
        window.activate(track_index(window, 1))
        window._poll_transport()
        assert window.picture_fills_window is False
        assert window._tray.isVisible()

    def test_the_button_fills_the_window(self, window) -> None:
        window.activate(track_index(window, 1))
        window._poll_transport()
        window.picture_surface.size_button.click()
        assert window.picture_fills_window is True
        assert window._tray.isVisible() is False
        assert window._position_bar.isVisible() is False
        assert window._bottom_tray.isVisible() is False

    def test_the_same_button_puts_it_back(self, window) -> None:
        """One control, reading the other way once it has been pressed."""
        window.activate(track_index(window, 1))
        window._poll_transport()
        window.picture_surface.size_button.click()
        assert window.picture_surface.size_button.filling is True
        window.picture_surface.size_button.click()
        assert window.picture_fills_window is False
        assert window._tray.isVisible()
        assert window.picture_surface.size_button.filling is False

    def test_escape_puts_it_back(self, window) -> None:
        window.activate(track_index(window, 1))
        window._poll_transport()
        window.fill_window_with_picture()
        window.shrink_picture()
        assert window.picture_fills_window is False
        assert window._tray.isVisible()

    def test_escape_answers_only_while_it_fills_the_window(self, window) -> None:
        """So the key is left to whatever else wants it the rest of the time."""
        window.activate(track_index(window, 1))
        window._poll_transport()
        assert window._picture_escape.isEnabled() is False
        window.fill_window_with_picture()
        assert window._picture_escape.isEnabled() is True
        window.shrink_picture()
        assert window._picture_escape.isEnabled() is False

    def test_a_track_ending_gives_the_window_back_too(self, window) -> None:
        """Otherwise the library returns with no toolbar around it."""
        window.activate(track_index(window, 1))
        window._poll_transport()
        window.fill_window_with_picture()
        window.activate(track_index(window, 0))
        window._poll_transport()
        assert window.picture_fills_window is False
        assert window._tray.isVisible()
        assert window._position_bar.isVisible()

    def test_nothing_fills_the_window_when_no_picture_is_showing(self, window) -> None:
        window.activate(track_index(window, 0))
        window._poll_transport()
        window.fill_window_with_picture()
        assert window.picture_fills_window is False


class TestTheButtonItself:
    def test_it_is_a_keyboard_stop(self, window) -> None:
        """Nothing here is reachable only by mouse."""
        from PySide6.QtCore import Qt

        assert window.picture_surface.size_button.focusPolicy() != (
            Qt.FocusPolicy.NoFocus
        )

    def test_it_says_what_a_press_would_do(self, window) -> None:
        button = window.picture_surface.size_button
        assert button.toolTip() == "Fill the window"
        button.set_filling(True)
        assert button.toolTip() == "Put the picture back"

    def test_it_stays_up_at_the_library_size(self, window) -> None:
        """It shares the window there, so it takes nothing away."""
        window.activate(track_index(window, 1))
        window._poll_transport()
        assert window.picture_surface.size_button.isVisible()

    def test_it_sits_in_the_corner_of_the_surface(self, window) -> None:
        window.activate(track_index(window, 1))
        window._poll_transport()
        surface = window.picture_surface
        button = surface.size_button
        assert button.geometry().right() < surface.width()
        assert button.geometry().bottom() < surface.height()


class TestDrawingAtItsOwnSize:
    def test_a_small_picture_is_not_blown_up(self, window, player) -> None:
        """Four copies of one pixel is not detail; it is a blur."""
        window.activate(track_index(window, 1))
        reached(player, 500)
        window._poll_transport()
        window._tick_picture()
        surface = window.picture_surface
        drawn = surface.picture_rect()
        assert surface.width() > WIDTH
        assert drawn.width() == WIDTH
        assert drawn.height() == HEIGHT

    def test_a_picture_larger_than_the_surface_is_fitted(self, window) -> None:
        """Never larger than it is; smaller when there is no room for it."""
        surface = window.picture_surface
        surface.show_picture(
            Picture(width=4000, height=2000, data=bytes(4000 * 2000 * 3))
        )
        drawn = surface.picture_rect()
        assert drawn.width() <= surface.width()
        assert drawn.height() <= surface.height()

    def test_it_is_centred_either_way(self, window, player) -> None:
        window.activate(track_index(window, 1))
        reached(player, 500)
        window._poll_transport()
        window._tick_picture()
        surface = window.picture_surface
        drawn = surface.picture_rect()
        assert abs(drawn.left() - (surface.width() - drawn.width()) // 2) <= 1
        assert abs(drawn.top() - (surface.height() - drawn.height()) // 2) <= 1


class TestFillingMakesItLarger:
    def test_filling_the_window_enlarges_the_picture(self, window, player) -> None:
        """Asking for the whole window is asking to see it larger."""
        window.activate(track_index(window, 1))
        reached(player, 500)
        window._poll_transport()
        window._tick_picture()
        small = window.picture_surface.picture_rect()
        window.fill_window_with_picture()
        window._tick_picture()
        large = window.picture_surface.picture_rect()
        assert large.width() > small.width()
        assert large.height() > small.height()

    def test_filled_it_reaches_an_edge_of_the_surface(self, window, player) -> None:
        """As large as the shape allows, which is what filling means."""
        window.activate(track_index(window, 1))
        reached(player, 500)
        window._poll_transport()
        window.fill_window_with_picture()
        window._tick_picture()
        surface = window.picture_surface
        drawn = surface.picture_rect()
        assert drawn.width() == surface.width() or drawn.height() == surface.height()

    def test_putting_it_back_returns_it_to_its_own_size(self, window, player) -> None:
        """Its own size, not whatever the surface happens to be."""
        window.activate(track_index(window, 1))
        reached(player, 500)
        window._poll_transport()
        window._tick_picture()
        window.fill_window_with_picture()
        window.shrink_picture()
        window._tick_picture()
        drawn = window.picture_surface.picture_rect()
        assert (drawn.width(), drawn.height()) == (WIDTH, HEIGHT)
