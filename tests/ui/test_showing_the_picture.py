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
from playback_support import BareStore
from PySide6.QtWidgets import QApplication

from stellody.application.pictures import Pictures
from stellody.application.scan import LoadLibrary, ScanLibrary
from stellody.application.transport import Transport
from stellody.domain.album import Album
from stellody.domain.identity import AlbumIdentity
from stellody.domain.picture import Picture
from stellody.domain.playback import PlaybackPosition
from stellody.domain.track import CD_SAMPLE_RATE, Track, TrackSource

TRACK_FRAMES = CD_SAMPLE_RATE * 10
WIDTH = 2
HEIGHT = 2


def a_picture(value: int) -> Picture:
    """A tiny frame carrying a value, so one can be told from another."""
    return Picture(
        width=WIDTH, height=HEIGHT, data=bytes([value]) * (WIDTH * HEIGHT * 3)
    )


class FakePictures:
    """A picture port that hands back the moment it was asked for."""

    def __init__(self, source: TrackSource) -> None:
        self.source = source
        self.closed = False
        self.asked: list[int] = []

    def picture_at(self, elapsed_ms: int) -> Picture:
        self.asked.append(elapsed_ms)
        return a_picture(min(255, elapsed_ms % 256))

    def close(self) -> None:
        self.closed = True


def named_track(number: int, path: str) -> Track:
    """One track of an album, its kind decided by its path."""
    return Track(
        source=TrackSource(path=path),
        disc_number=1,
        track_number=number,
        title=f"Track {number}",
        artists=("Holst",),
        duration_ms=10000,
        sample_rate=CD_SAMPLE_RATE,
        bit_depth=16,
    )


def album() -> Album:
    """An album whose second track is a bonus video, as a real one is."""
    return Album(
        identity=AlbumIdentity(album_artist="Holst", title="The Planets"),
        tracks=(named_track(1, "01 Song.flac"), named_track(2, "02 Bonus.m4v")),
    )


@pytest.fixture
def player() -> RecordingPlayer:
    return RecordingPlayer()


@pytest.fixture
def window(application: QApplication, player: RecordingPlayer):
    """A window with a picture service over the fake port."""
    from stellody.ui.main_window import MainWindow

    store = BareStore()

    def session():
        return ScanLibrary(None, None, None, store), store

    made = MainWindow(
        scan_session=session,
        loader=LoadLibrary(store),
        transport=Transport(player),
        settings=store,
        pictures=Pictures(FakePictures),
    )
    made._model.set_albums((album(),))
    made.show()
    application.processEvents()
    return made


def track_index(window, row: int):
    """One track under the only album."""
    return window._model.index(row, 0, window._model.index(0, 0))


def reached(player: RecordingPlayer, ms: int) -> None:
    """Say the sound has played that far, as a device would report it."""
    player.reported = PlaybackPosition(
        frame=ms * CD_SAMPLE_RATE // 1000,
        frame_count=TRACK_FRAMES,
        sample_rate=CD_SAMPLE_RATE,
    )


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
