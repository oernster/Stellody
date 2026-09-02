"""The window, the album and the device the highlight tests are driven against.

Shared by the tests for the library tree and by those for the album open under
the sleeves, because the rule is one rule: the highlight follows the transport
rather than the mouse, in whichever view is on show.
"""

from __future__ import annotations

import pytest
from conftest import RecordingPlayer
from PySide6.QtWidgets import QApplication

from stellody.application.scan import LoadLibrary, ScanLibrary
from stellody.application.transport import Transport
from stellody.domain.album import Album
from stellody.domain.identity import AlbumIdentity
from stellody.domain.overrides import Override
from stellody.domain.track import CD_SAMPLE_RATE, Track, TrackSource
from stellody.ui.main_window import MainWindow
from stellody.ui.settings_keys import SETTING_ROOT

ROOT = "H:/FLACMusic"
FIRST_ALBUM_ROW = 0
TRACK_COUNT = 3
# Enough polls that a highlight being dragged back would show up.
POLLS = 5


def track(number: int) -> Track:
    """One ordinary track."""
    return Track(
        source=TrackSource(path=f"{number}.flac"),
        disc_number=1,
        track_number=number,
        title=f"Track {number}",
        artists=("Holst",),
        duration_ms=1000,
        sample_rate=CD_SAMPLE_RATE,
        bit_depth=16,
    )


def album() -> Album:
    """One album of three tracks, so a middle one exists to move off."""
    return Album(
        identity=AlbumIdentity(album_artist="Holst", title="The Planets"),
        tracks=tuple(track(number) for number in range(1, TRACK_COUNT + 1)),
    )


class BareStore:
    """Enough of a store for a window that never scans."""

    def __init__(self) -> None:
        self.settings = {SETTING_ROOT: ROOT}
        self.accepted: tuple[Override, ...] = ()

    def all_overrides(self) -> tuple[Override, ...]:
        """Nothing accepted, which is what a library nobody has touched holds."""
        return self.accepted

    def accept_overrides(self, accepted: tuple[Override, ...]) -> None:
        """Keep what was accepted, so a test can read it back."""
        self.accepted = self.accepted + accepted

    def discard_overrides(self, unwanted: tuple[Override, ...]) -> None:
        """Drop pins by what they apply to, the value not being part of it."""
        dropped = {(item.album, item.path, item.field) for item in unwanted}
        self.accepted = tuple(
            item
            for item in self.accepted
            if (item.album, item.path, item.field) not in dropped
        )

    def load_folders(self) -> tuple:
        """Nothing remembered."""
        return ()

    def file_signatures(self) -> dict:
        """Nothing on record."""
        return {}

    def save_folder(self, record) -> None:
        """Never called here."""

    def mark_absent(self, seen_paths) -> int:
        """Nothing went missing."""
        return 0

    def get_setting(self, key: str, default: str = "") -> str:
        """One stored setting."""
        return self.settings.get(key, default)

    def set_setting(self, key: str, value: str) -> None:
        """Store one setting."""
        self.settings[key] = value

    def close(self) -> None:
        """Nothing to release."""


@pytest.fixture
def player() -> RecordingPlayer:
    """A device that records rather than plays."""
    return RecordingPlayer()


@pytest.fixture
def window(application: QApplication, player: RecordingPlayer) -> MainWindow:
    """A real window over that device, holding one album of three tracks."""
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
    return made


def album_index(window: MainWindow):
    """The index of the only album."""
    return window._model.index(FIRST_ALBUM_ROW, 0)


def track_index(window: MainWindow, row: int):
    """The index of one track under that album."""
    return window._model.index(row, 0, album_index(window))


def highlighted(window: MainWindow) -> Track | None:
    """The track the library is pointing at right now."""
    return window._model.track_at(window._tree.currentIndex())
