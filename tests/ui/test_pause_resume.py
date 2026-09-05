"""Pausing and resuming holds position; only starting a track reloads it.

Reported as playback jumping back to the top of a track after a few presses.
A reload is what restarts a track, so what is asserted throughout is the
sequence of commands the device was given: a resume that reloads is the fault,
whatever it looks like on screen.
"""

from __future__ import annotations

import pytest
from conftest import RecordingPlayer
from PySide6.QtCore import QPoint
from PySide6.QtWidgets import QApplication

from stellody.application.scan import LoadLibrary, ScanLibrary
from stellody.application.transport import Transport
from stellody.domain.album import Album
from stellody.domain.identity import AlbumIdentity
from stellody.domain.overrides import AlbumEdit, Override
from stellody.domain.track import CD_SAMPLE_RATE, Track, TrackSource
from stellody.ui.main_window import MainWindow
from stellody.ui.settings_keys import SETTING_ROOT

ROOT = "H:/FLACMusic"
FIRST_ALBUM_ROW = 0
TRACK_COUNT = 3
CYCLES = 4


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
    """One album of three tracks."""
    return Album(
        identity=AlbumIdentity(album_artist="Holst", title="The Planets"),
        tracks=tuple(track(number) for number in range(1, TRACK_COUNT + 1)),
    )


class BareStore:
    """Enough of a store for a window that never scans."""

    def __init__(self) -> None:
        self.settings = {SETTING_ROOT: ROOT}

    def all_overrides(self) -> tuple[Override, ...]:
        """Nothing accepted; these stores stand in for an untouched library."""
        return ()

    def all_album_edits(self) -> tuple[AlbumEdit, ...]:
        """Nothing stated either, for the same reason."""
        return ()

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
    """A real window over that device, holding one album."""
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


def menu_action(window: MainWindow, name: str, over=None):
    """One item of the menu the library offers on a right click.

    Raised over a given row, because the menu reads the row under the cursor;
    over nothing when no row is named, which is the empty space below the
    library.
    """
    where = QPoint(0, 0) if over is None else window._tree.visualRect(over).center()
    window.show_transport_menu(where)
    return {action.text(): action for action in window._menu.actions()}[name]


def test_the_tray_button_holds_position_over_many_presses(
    window: MainWindow, player: RecordingPlayer
) -> None:
    window.activate(track_index(window, 0))
    player.calls.clear()
    for _ in range(CYCLES):
        window.toggle_playback()
        window.toggle_playback()
    assert player.calls == ["pause", "play"] * CYCLES
    assert "load" not in player.calls, "a reload is what restarts a track"


def test_the_menu_pause_then_play_holds_position(
    window: MainWindow, player: RecordingPlayer
) -> None:
    """The two items are named for actions, so each has to do just its own."""
    playing = track_index(window, 0)
    window.activate(playing)
    player.calls.clear()
    for _ in range(CYCLES):
        menu_action(window, "Pause", playing).trigger()
        menu_action(window, "Play", playing).trigger()
    assert player.calls == ["pause", "play"] * CYCLES
    assert "load" not in player.calls


def test_menu_pause_pressed_twice_does_not_start_playing_again(
    window: MainWindow, player: RecordingPlayer
) -> None:
    """An item called Pause pauses. Pressing it again cannot mean resume."""
    playing = track_index(window, 0)
    window.activate(playing)
    player.calls.clear()
    menu_action(window, "Pause", playing).trigger()
    action = menu_action(window, "Pause", playing)
    assert not action.isEnabled(), "nothing is playing to pause"
    assert player.calls == ["pause"]


def test_menu_play_on_the_track_already_paused_resumes_it(
    window: MainWindow, player: RecordingPlayer
) -> None:
    """Play on the track in hand means carry on, never start it over.

    This is the reported fault. The highlight follows the transport, so the
    row under the cursor IS the paused track, which made Play reload it.
    """
    paused = track_index(window, 1)
    window.activate(paused)
    window.toggle_playback()
    player.calls.clear()
    menu_action(window, "Play", paused).trigger()
    assert player.calls == ["play"], "resumed rather than reloaded"


def test_menu_play_on_a_different_track_starts_that_one(
    window: MainWindow, player: RecordingPlayer
) -> None:
    """Choosing another row is asking for that row, so it does load."""
    window.activate(track_index(window, 0))
    window.toggle_playback()
    player.calls.clear()
    other = track_index(window, 2)
    menu_action(window, "Play", other).trigger()
    assert player.calls == ["load", "play"]
    assert window._transport.current.title == "Track 3"


def test_play_is_not_offered_over_the_track_already_playing(
    window: MainWindow,
) -> None:
    """There is nothing for it to do, so it says so rather than pausing."""
    playing = track_index(window, 0)
    window.activate(playing)
    assert not menu_action(window, "Play", playing).isEnabled()


def test_play_over_empty_space_resumes_what_is_paused(
    window: MainWindow, player: RecordingPlayer
) -> None:
    """Away from any row there is no track being asked for, only the one loaded."""
    window.activate(track_index(window, 0))
    window.toggle_playback()
    player.calls.clear()
    action = menu_action(window, "Play")
    assert action.isEnabled()
    action.trigger()
    assert player.calls == ["play"]
