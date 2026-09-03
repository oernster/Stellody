"""The transport as the window drives it.

The application layer decides what the buttons mean and is tested separately;
these assert the wiring: that activating a row reaches the transport, that the
buttons offer only what can be done, that the device is given back when the
window goes. Qt is never mocked; only the device is.
"""

from __future__ import annotations

import pytest
from conftest import RecordingPlayer
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
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
NO_MODIFIER = Qt.KeyboardModifier.NoModifier


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


class BareStore:
    """Enough of a store for a window that never scans."""

    def __init__(self) -> None:
        self.settings = {SETTING_ROOT: ROOT}

    def all_overrides(self) -> tuple[Override, ...]:
        """Nothing accepted; these stores stand in for an untouched library."""
        return ()

    def load_folders(self) -> tuple:
        """Nothing remembered; the tests put albums in the model directly."""
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
def window(application: QApplication) -> MainWindow:
    """A real window over a recording player, showing one album."""
    store = BareStore()
    player = RecordingPlayer()

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


def album_index(window: MainWindow):
    """The index of the only album in the model."""
    return window._model.index(FIRST_ALBUM_ROW, 0)


def track_index(window: MainWindow, row: int):
    """The index of one track under that album."""
    return window._model.index(row, 0, album_index(window))


def test_activating_a_track_plays_it(window: MainWindow) -> None:
    window.activate(track_index(window, 1))
    assert window._player.calls == ["load", "play"]
    assert window._transport.current.title == "Track 2"


def test_activating_an_album_row_plays_nothing(window: MainWindow) -> None:
    """An album is a container: opening it means showing what is inside."""
    window.activate(album_index(window))
    assert window._player.calls == []


def test_the_transport_is_offered_only_once_there_is_something_to_play(
    window: MainWindow,
) -> None:
    for button in window._tray.transport_stops():
        assert button.isEnabled() is False
    window.activate(track_index(window, 0))
    assert window._tray.previous_button.isEnabled() is True
    assert window._tray.play_button.isEnabled() is True


def test_stop_is_offered_only_while_a_device_is_open(window: MainWindow) -> None:
    window.activate(track_index(window, 0))
    assert window._tray.stop_button.isEnabled() is True
    window.stop_playback()
    assert window._tray.stop_button.isEnabled() is False


def test_the_play_button_shows_what_pressing_it_would_do(
    window: MainWindow,
) -> None:
    """Playing shows pause, as the theme toggle shows the theme it switches to."""
    window.activate(track_index(window, 0))
    assert window._tray.play_button.toolTip() == "Pause"
    window.toggle_playback()
    assert window._player.calls[-1] == "pause"
    assert window._tray.play_button.toolTip() == "Play"


def test_the_buttons_move_through_the_album(window: MainWindow) -> None:
    """Back twice, since a single press starts the track in hand again."""
    window.activate(track_index(window, 0))
    window.next_track()
    assert window._transport.current.title == "Track 2"
    window.previous_track()
    assert window._transport.current.title == "Track 2", "the first press restarts"
    window.previous_track()
    assert window._transport.current.title == "Track 1"


def test_a_finished_track_moves_on_without_anybody_pressing_anything(
    window: MainWindow,
) -> None:
    """The device raises no event at the end of a track, so a timer asks."""
    window.activate(track_index(window, 0))
    window._player.finished = True
    window._poll_transport()
    assert window._transport.current.title == "Track 2"


def test_quitting_gives_the_device_back(window: MainWindow) -> None:
    """A held device outliving the window is a process nobody can see."""
    window.activate(track_index(window, 0))
    window.quit_application()
    assert window._player.calls[-1] == "stop"
    assert window._transport_timer.isActive() is False


def test_a_track_that_will_not_open_is_reported_rather_than_silent(
    window: MainWindow,
) -> None:
    """An exception inside a Qt slot ends the slot with nothing said."""

    def refuse(source, request):
        raise RuntimeError("device is held by another application")

    window._player.load = refuse
    window.activate(track_index(window, 0))
    assert "Track 1 could not be played" in window.statusBar().currentMessage()
    assert "another application" in window.statusBar().currentMessage()


def test_a_refused_track_leaves_the_transport_offering_nothing(
    window: MainWindow,
) -> None:
    def refuse(source, request):
        raise OSError("file has gone")

    window._player.load = refuse
    window.activate(track_index(window, 0))
    assert window._tray.stop_button.isEnabled() is False


def menu_items(window: MainWindow, where) -> dict:
    """The context menu the tree would show at a point, by label."""
    window.show_transport_menu(where)
    return {action.text(): action for action in window._menu.actions() if action.text()}


def point_of(window: MainWindow, index) -> object:
    """A point inside the row for an index."""
    return window._tree.visualRect(index).center()


def test_double_clicking_a_track_plays_it(window: MainWindow) -> None:
    """A real double click, because the point is which signals that emits.

    Measured on this tree: one double click emits BOTH doubleClicked and
    activated, so connecting the pair loads the track twice and restarts it
    audibly. A test that emitted a signal by hand would pass either way, which
    is why this drives the mouse.
    """
    window.show()
    window._tree.expandAll()
    QApplication.processEvents()
    index = track_index(window, 0)
    window._tree.scrollTo(index)
    spot = window._tree.visualRect(index).center()
    QTest.mouseClick(
        window._tree.viewport(), Qt.MouseButton.LeftButton, NO_MODIFIER, spot
    )
    QTest.mouseDClick(
        window._tree.viewport(), Qt.MouseButton.LeftButton, NO_MODIFIER, spot
    )
    QApplication.processEvents()
    assert window._player.calls == ["load", "play"]
    assert window._transport.current.title == "Track 1"


def test_return_on_a_track_plays_it_too(window: MainWindow) -> None:
    """Measured: Return emits activated, which a double click does not."""
    window._tree.activated.emit(track_index(window, 1))
    assert window._transport.current.title == "Track 2"


def test_the_right_click_menu_offers_the_whole_transport(
    window: MainWindow,
) -> None:
    window._tree.expandAll()
    items = menu_items(window, point_of(window, track_index(window, 0)))
    assert list(items) == ["Play", "Pause", "Stop", "Previous track", "Next track"]


def test_play_over_a_track_plays_that_track(window: MainWindow) -> None:
    window._tree.expandAll()
    items = menu_items(window, point_of(window, track_index(window, 1)))
    items["Play"].trigger()
    assert window._transport.current.title == "Track 2"


def test_the_menu_offers_only_what_can_be_done_right_now(
    window: MainWindow,
) -> None:
    window._tree.expandAll()
    idle = menu_items(window, point_of(window, album_index(window)))
    assert idle["Play"].isEnabled() is True, "an album row starts its album"
    assert idle["Pause"].isEnabled() is False
    assert idle["Stop"].isEnabled() is False
    assert idle["Next track"].isEnabled() is False

    window.activate(track_index(window, 0))
    playing = menu_items(window, point_of(window, album_index(window)))
    assert playing["Pause"].isEnabled() is True
    assert playing["Stop"].isEnabled() is True
    assert playing["Next track"].isEnabled() is True
    assert playing["Previous track"].isEnabled() is True, "back restarts it"


def test_play_over_an_album_row_starts_that_album(window: MainWindow) -> None:
    """The same everywhere: a row naming an album plays it, list or grid.

    It used to be dead here, on the reading that an album row carries no track
    of its own. So does a sleeve; pressing Play on one plainly means play
    this. Leaving the list behind the grid would be the same gesture
    answering in two different ways.
    """
    window._tree.expandAll()
    menu_items(window, point_of(window, album_index(window)))["Play"].trigger()
    assert window._transport.current.title == "Track 1"


def test_pausing_from_the_menu_pauses(window: MainWindow) -> None:
    window._tree.expandAll()
    window.activate(track_index(window, 0))
    menu_items(window, point_of(window, album_index(window)))["Pause"].trigger()
    assert window._player.calls[-1] == "pause"


def test_play_away_from_a_track_resumes_what_is_loaded(window: MainWindow) -> None:
    window._tree.expandAll()
    window.activate(track_index(window, 0))
    window.toggle_playback()
    items = menu_items(window, point_of(window, album_index(window)))
    assert items["Play"].isEnabled() is True
    items["Play"].trigger()
    assert window._player.calls[-1] == "play"


def test_the_play_button_starts_the_track_that_is_selected(
    window: MainWindow,
) -> None:
    """A play button that does nothing until something else started a track."""
    window._tree.expandAll()
    assert window._tray.play_button.isEnabled() is False
    window._tree.setCurrentIndex(track_index(window, 1))
    assert window._tray.play_button.isEnabled() is True
    window.toggle_playback()
    assert window._transport.current.title == "Track 2"
    assert window._player.calls == ["load", "play"]


def test_selecting_an_album_row_leaves_play_unpressable(
    window: MainWindow,
) -> None:
    """An album is a container; there is no one track to start."""
    window._tree.setCurrentIndex(album_index(window))
    assert window._tray.play_button.isEnabled() is False
