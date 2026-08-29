"""The library highlights whatever is playing, however it came to be playing.

Reported as three separate faults and they are one: the tray buttons, the right
click menu and a track ending all move the transport; none of them moved the
highlight, so the library went on pointing at whatever was last clicked.
The highlight is how a listener finds their place, so it follows the transport
rather than the mouse.
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


def test_activating_a_track_leaves_the_highlight_on_it(window: MainWindow) -> None:
    """The starting point: what is played is what is pointed at."""
    window.activate(track_index(window, 0))
    assert highlighted(window) is window._transport.current


def test_the_next_button_carries_the_highlight_with_it(window: MainWindow) -> None:
    window.activate(track_index(window, 0))
    window.next_track()
    assert window._transport.current.title == "Track 2"
    assert highlighted(window) is window._transport.current


def test_the_previous_button_carries_the_highlight_with_it(
    window: MainWindow,
) -> None:
    window.activate(track_index(window, 2))
    window.previous_track()
    window.previous_track()
    assert window._transport.current.title == "Track 2"
    assert highlighted(window) is window._transport.current


def test_a_track_playing_out_carries_the_highlight_to_the_next_one(
    window: MainWindow, player: RecordingPlayer
) -> None:
    """Nobody pressed anything, so this is the one that matters most."""
    window.activate(track_index(window, 0))
    player.finished = True
    window._poll_transport()
    assert window._transport.current.title == "Track 2"
    assert highlighted(window) is window._transport.current


def test_jumping_across_the_album_carries_the_highlight(window: MainWindow) -> None:
    """Activating a track well away from the highlight moves it there."""
    window.activate(track_index(window, 0))
    window.activate(track_index(window, 2))
    assert window._transport.current.title == "Track 3"
    assert highlighted(window) is window._transport.current


def test_the_highlight_follows_a_shuffled_queue_rather_than_the_rows(
    window: MainWindow,
) -> None:
    """Shuffle changes what comes next, so the highlight has to be looked up."""
    window.activate(track_index(window, 0))
    window.toggle_shuffle()
    window.next_track()
    assert highlighted(window) is window._transport.current


def test_stopping_leaves_the_highlight_where_the_music_stopped(
    window: MainWindow,
) -> None:
    """Stop gives the device back; it does not move anybody's place."""
    window.activate(track_index(window, 1))
    stopped = window._transport.current
    window.stop_playback()
    assert highlighted(window) is stopped


def test_a_poll_that_changes_nothing_leaves_the_highlight_alone(
    window: MainWindow,
) -> None:
    """Four polls a second must not drag the listener back from browsing."""
    window.activate(track_index(window, 0))
    window._tree.setCurrentIndex(track_index(window, 2))
    for _ in range(POLLS):
        window._poll_transport()
    assert window._transport.current.title == "Track 1", "nothing finished"
    assert highlighted(window).title == "Track 3", "the browse position stood"


def test_the_right_click_menu_carries_the_highlight_too(window: MainWindow) -> None:
    """The menu was reported separately; it is the same wiring underneath."""
    window.activate(track_index(window, 0))
    window.show_transport_menu(QPoint(0, 0))
    actions = {action.text(): action for action in window._menu.actions()}
    actions["Next track"].trigger()
    assert window._transport.current.title == "Track 2"
    assert highlighted(window) is window._transport.current
    window.show_transport_menu(QPoint(0, 0))
    actions = {action.text(): action for action in window._menu.actions()}
    actions["Previous track"].trigger()
    actions["Previous track"].trigger()
    assert window._transport.current.title == "Track 1"
    assert highlighted(window) is window._transport.current


def test_a_track_inside_a_collapsed_album_is_shown_before_it_is_highlighted(
    window: MainWindow,
) -> None:
    """A highlight on a hidden row is a highlight nobody can see."""
    window._tree.collapse(album_index(window))
    window.activate(track_index(window, 1))
    assert window._tree.isExpanded(album_index(window))
    assert highlighted(window) is window._transport.current


def played_out(window: MainWindow, player: RecordingPlayer, steps: int) -> list[str]:
    """The titles heard as the poll carries one track into the next.

    Driven through the window's own timer slot rather than the transport, so
    what is asserted is what a listener sitting in front of it would hear.
    """
    heard = [window._transport.current.title]
    for _ in range(steps):
        player.finished = True
        window._poll_transport()
        heard.append(window._transport.current.title)
    return heard


def test_an_album_left_to_play_out_stops_at_its_end(
    window: MainWindow, player: RecordingPlayer
) -> None:
    """Without repeat the end is the end, which is what repeat is measured on."""
    window.activate(track_index(window, 0))
    heard = played_out(window, player, 4)
    assert heard == ["Track 1", "Track 2", "Track 3", "Track 3", "Track 3"]
    assert window._transport.playing is False


def test_a_repeating_album_starts_again_rather_than_stopping(
    window: MainWindow, player: RecordingPlayer
) -> None:
    """The album until repeat is turned off, never one track over and over."""
    window.activate(track_index(window, 0))
    window.toggle_repeat()
    heard = played_out(window, player, 5)
    assert heard == ["Track 1", "Track 2", "Track 3", "Track 1", "Track 2", "Track 3"]


def test_a_repeating_shuffled_album_is_scattered_again_for_the_next_time_round(
    window: MainWindow, player: RecordingPlayer
) -> None:
    """The order is asked for once a time round, with the whole album given."""
    asked: list[int] = []
    window._transport._ordering = lambda given: asked.append(len(given)) or given
    window.activate(track_index(window, 0))
    window.toggle_shuffle()
    window.toggle_repeat()
    scattered_when_switched_on = len(asked)
    heard = played_out(window, player, 3)
    assert len(asked) == scattered_when_switched_on + 1, "once, at the join"
    assert set(heard) == {"Track 1", "Track 2", "Track 3"}
