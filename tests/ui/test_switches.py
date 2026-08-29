"""The tray switches as the window drives them, plus the two buttons beside them.

Three switches that outlast the track in hand. Each has to reach the transport,
show its own state and be there again next time the application opens; a switch
that does two of those and not the third is the one that gets reported as a bug.

What is asserted about the pictures is that the two states DIFFER, not what the
artwork is: the strike is a composite made at run time, so comparing it to a
stored image would be testing the drawing rather than the wiring.

The donate button is the one thing here that leaves the application, so what is
asserted is the address handed outward, through a seam of our own rather than
by mocking Qt or by opening a browser in the middle of a test run.
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
from stellody.shared.version import DONATE_URL
from stellody.ui import main_window as window_module
from stellody.ui.main_window import MainWindow
from stellody.ui.settings_keys import (
    FALSE,
    SETTING_MUTED,
    SETTING_REPEAT,
    SETTING_SHUFFLE,
    TRUE,
)

ICON_PX = 30
# Long enough for the walk to come back round to where it started.
RING_WALK = 40
# Written out rather than read from the source it is checking. Comparing the
# constant against itself passes whatever it is changed to, which for a payment
# address is the one change that must never happen quietly.
EXPECTED_DONATE_URL = "https://www.paypal.com/ncp/payment/QGC2XK2Z5WNUW"


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


def test_the_view_toggle_sits_at_the_left_of_the_strip(window: MainWindow) -> None:
    """Under the library it would change, away from the settings.

    Read off the layout as well as off the geometry. A button never added to
    the layout also sits at the left, at nothing, which a comparison of
    positions alone reports as a pass.
    """
    window.show()
    tray = window._bottom_tray
    row = tray.layout()
    widgets = [row.itemAt(position).widget() for position in range(row.count())]
    assert tray.view_button in widgets, "the toggle is actually laid out"
    # The one item holding no widget is the stretch that splits the strip.
    gap = widgets.index(None)
    assert widgets.index(tray.view_button) < gap, "the toggle is before the gap"
    for button in tray.switch_stops():
        assert widgets.index(button) > gap, "every setting is after it"
    view = tray.view_button.mapTo(tray, tray.view_button.rect().center()).x()
    switches = [
        button.mapTo(tray, button.rect().center()).x() for button in tray.switch_stops()
    ]
    assert view < min(switches), "and it is drawn there too"


def test_the_view_toggle_says_it_is_not_built_rather_than_doing_nothing(
    window: MainWindow,
) -> None:
    """Nothing reads album art yet, so the button admits it."""
    button = window._bottom_tray.view_button
    assert not button.isEnabled()
    assert "not built yet" in button.toolTip()
    assert not button.icon().isNull(), "it is drawn, not merely reserved"


def test_the_disabled_view_toggle_is_not_a_stop_but_is_named_as_one(
    application: QApplication, window: MainWindow
) -> None:
    """Named now so the ring picks it up the day it works, skipped until then."""
    tray = window._bottom_tray
    assert tray.view_button in tray.ring_stops()
    window.show()
    application.processEvents()
    order = []
    seen: set[int] = set()
    for _ in range(RING_WALK):
        window.focusNextChild()
        current = application.focusWidget()
        if current is None or id(current) in seen:
            break
        seen.add(id(current))
        order.append(current)
    assert tray.view_button not in order, "a disabled control is never a stop"
    assert tray.volume_button in order, "the enabled ones still are"


def test_the_donate_button_sits_outside_everything_else(window: MainWindow) -> None:
    """It belongs to nothing on screen, so it sits where nothing else is."""
    window.show()
    tray = window._bottom_tray
    row = tray.layout()
    widgets = [row.itemAt(position).widget() for position in range(row.count())]
    assert widgets[0] is tray.donate_button, "first in the row, before the toggle"
    assert tray.donate_button in tray.ring_stops()
    assert tray.donate_button.isEnabled(), "unlike the view toggle, this one works"
    assert "opens your browser" in tray.donate_button.toolTip()


def test_pressing_donate_asks_the_desktop_for_that_one_address(
    window: MainWindow, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The seam is stood in front of, so no browser opens in a test run."""
    asked: list[str] = []
    monkeypatch.setattr(
        window_module, "open_externally", lambda address: asked.append(address) or True
    )
    window._bottom_tray.donate_button.click()
    assert asked == [EXPECTED_DONATE_URL]
    assert DONATE_URL == EXPECTED_DONATE_URL, "the address changed"
    assert DONATE_URL.startswith("https://"), "never handed out over plain http"


def test_a_desktop_that_will_not_open_a_browser_says_so(
    window: MainWindow, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Silence would leave a button that appears to do nothing at all."""
    monkeypatch.setattr(window_module, "open_externally", lambda address: False)
    window._bottom_tray.donate_button.click()
    assert "Could not open a browser" in window.statusBar().currentMessage()
