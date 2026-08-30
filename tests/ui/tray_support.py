"""The window and the album the tray tests are driven against.

Shared by the tests for the switches and by the tests for the volume, because
both need a real window over a store that remembers and a device that records.
Kept out of conftest so it stays visible at the point of use. Several other
window tests here define their own fixtures under the same names; one of those
quietly shadowing a shared one is harder to read than an import.
"""

from __future__ import annotations

from conftest import RecordingPlayer
from PySide6.QtGui import QImage

from stellody.application.scan import LoadLibrary, ScanLibrary
from stellody.application.transport import Transport
from stellody.domain.album import Album
from stellody.domain.identity import AlbumIdentity
from stellody.domain.track import CD_SAMPLE_RATE, Track, TrackSource
from stellody.ui.main_window import MainWindow

ICON_PX = 30


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
    """One album of two tracks."""
    return Album(
        identity=AlbumIdentity(album_artist="Holst", title="The Planets"),
        tracks=(track(1), track(2)),
    )


class RememberingStore:
    """Enough of a store to answer a window, keeping what it is told."""

    def __init__(self, settings: dict[str, str] | None = None) -> None:
        self.settings = dict(settings or {})

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


def build(
    store: RememberingStore,
    player: RecordingPlayer,
    leave=None,
    chooser=None,
) -> MainWindow:
    """A real window over a recording player, holding one album.

    The chooser is left out by default, because a window built without one
    offers no cover lookup at all: that is what lets every test here raise the
    transport menu with no network in the room.
    """

    def session():
        return ScanLibrary(None, None, None, store), store

    made = MainWindow(
        scan_session=session,
        loader=LoadLibrary(store),
        transport=Transport(player),
        settings=store,
        leave=leave,
        chooser=chooser,
    )
    made._model.set_albums((album(),))
    return made


def picture(button) -> QImage:
    """One button's icon as an image, so two states can be told apart.

    A QImage rather than its raw bytes: reading bits() off a chain of
    temporaries hands back a buffer whose owner is already gone, which was
    measured here as a comparison that passed alone and failed in sequence.
    """
    return button.icon().pixmap(ICON_PX, ICON_PX).toImage()
