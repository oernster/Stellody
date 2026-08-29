"""Mute, shuffle and repeat as the window drives them.

Three switches that outlast the track in hand. Each has to reach the transport,
show its own state and be there again next time the application opens; a switch
that does two of those and not the third is the one that gets reported as a bug.

What is asserted about the pictures is that the two states DIFFER, not what the
artwork is: the strike is a composite made at run time, so comparing it to a
stored image would be testing the drawing rather than the wiring.
"""

from __future__ import annotations

import pytest
from conftest import RecordingPlayer
from PySide6.QtGui import QImage
from PySide6.QtWidgets import QApplication

from stellody.application.scan import LoadLibrary, ScanLibrary
from stellody.application.transport import Transport
from stellody.domain.album import Album
from stellody.domain.identity import AlbumIdentity
from stellody.domain.playback import SILENT_VOLUME, UNITY_VOLUME
from stellody.domain.track import CD_SAMPLE_RATE, Track, TrackSource
from stellody.ui.main_window import MainWindow
from stellody.ui.settings_keys import (
    FALSE,
    SETTING_MUTED,
    SETTING_REPEAT,
    SETTING_SHUFFLE,
    TRUE,
)

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


def build(store: RememberingStore, player: RecordingPlayer) -> MainWindow:
    """A real window over a recording player, holding one album."""

    def session():
        return ScanLibrary(None, None, None, store), store

    made = MainWindow(
        scan_session=session,
        loader=LoadLibrary(store),
        transport=Transport(player),
        settings=store,
    )
    made._model.set_albums((album(),))
    return made


@pytest.fixture
def store() -> RememberingStore:
    """A store that starts with nothing remembered."""
    return RememberingStore()


@pytest.fixture
def player() -> RecordingPlayer:
    """A device that records what it was asked for."""
    return RecordingPlayer()


@pytest.fixture
def window(
    application: QApplication, store: RememberingStore, player: RecordingPlayer
) -> MainWindow:
    """A window over that store and that device."""
    return build(store, player)


def picture(button) -> QImage:
    """One button's icon as an image, so two states can be told apart.

    A QImage rather than its raw bytes: reading bits() off a chain of
    temporaries hands back a buffer whose owner is already gone, which was
    measured here as a comparison that passed alone and failed in sequence.
    """
    return button.icon().pixmap(ICON_PX, ICON_PX).toImage()


def test_muting_silences_the_device_and_strikes_the_speaker_through(
    window: MainWindow, player: RecordingPlayer
) -> None:
    button = window._tray.mute_button
    unmuted = picture(button)
    window.toggle_mute()
    assert player.volume == SILENT_VOLUME
    assert button.toolTip() == "Unmute"
    assert picture(button) != unmuted, "the muted speaker is drawn struck through"
    window.toggle_mute()
    assert player.volume == UNITY_VOLUME
    assert button.toolTip() == "Mute"
    assert picture(button) == unmuted


def test_the_shuffle_switch_reaches_the_transport_and_changes_its_picture(
    window: MainWindow,
) -> None:
    button = window._bottom_tray.shuffle_button
    off = picture(button)
    window.toggle_shuffle()
    assert window._transport.shuffled is True
    assert button.toolTip() == "Turn shuffle off"
    assert picture(button) != off, "the switch is struck through only while off"
    window.toggle_shuffle()
    assert window._transport.shuffled is False
    assert picture(button) == off


def test_the_repeat_switch_reaches_the_transport_and_changes_its_picture(
    window: MainWindow,
) -> None:
    button = window._bottom_tray.repeat_button
    off = picture(button)
    window.toggle_repeat()
    assert window._transport.repeating is True
    assert button.toolTip() == "Turn repeat off"
    assert picture(button) != off
    window.toggle_repeat()
    assert window._transport.repeating is False
    assert picture(button) == off


def test_every_switch_is_written_down_as_it_is_pressed(
    window: MainWindow, store: RememberingStore
) -> None:
    for toggle, key in (
        (window.toggle_mute, SETTING_MUTED),
        (window.toggle_shuffle, SETTING_SHUFFLE),
        (window.toggle_repeat, SETTING_REPEAT),
    ):
        toggle()
        assert store.get_setting(key) == TRUE
        toggle()
        assert store.get_setting(key) == FALSE


def test_the_switches_come_back_as_they_were_left(
    application: QApplication, player: RecordingPlayer
) -> None:
    """A switch that forgets itself is the same as not having one."""
    remembered = RememberingStore(
        {SETTING_MUTED: TRUE, SETTING_SHUFFLE: TRUE, SETTING_REPEAT: TRUE}
    )
    reopened = build(remembered, player)
    assert reopened._transport.muted is True
    assert reopened._transport.shuffled is True
    assert reopened._transport.repeating is True
    assert reopened._tray.mute_button.toolTip() == "Unmute"
    assert reopened._bottom_tray.shuffle_button.toolTip() == "Turn shuffle off"
    assert player.volume == SILENT_VOLUME


def test_the_mute_switch_is_ruled_off_from_the_buttons_after_it(
    window: MainWindow,
) -> None:
    """It acts on what is playing; the two after it act on the application."""
    window.show()
    tray = window._tray
    separator = tray.separator
    assert separator.isVisible()
    centre = separator.mapTo(tray, separator.rect().center()).x()
    mute = tray.mute_button.mapTo(tray, tray.mute_button.rect().center()).x()
    theme = tray.theme_button.mapTo(tray, tray.theme_button.rect().center()).x()
    assert mute < centre < theme, "the line sits between the two groups"
    assert separator.focusPolicy() == 0, "a rule is not a control"
