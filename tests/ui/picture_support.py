"""What both picture suites need: a fake port, an album holding a video, a window.

Held here rather than in one suite and imported by the other, because importing
a fixture across test modules redefines its name and every linter says so. A
support module hands back plain functions; each suite wraps the ones it wants
in its own fixtures.
"""

from __future__ import annotations

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


def make_window(application: QApplication, player: RecordingPlayer):
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
