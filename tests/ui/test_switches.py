"""The tray under the menus as the window drives it: mute, the view, the sizes.

The bottom strip has its own module beside this one. What is left here is the
tray above, where a control is about what is playing or about what the library
is shown as rather than about what the library holds.

Mute is the one switch whose picture changes: a struck speaker says a press
would silence it. WHICH picture goes with which state is asserted here rather
than only that the two differ, since a test that asks only for a difference
passes just as happily with the two the wrong way round, which is how they
shipped that way. The strike is composed at run time, so the comparison is
against the same composition rather than against a file.

What is written down as a switch is pressed is asserted here too, for mute and
for shuffle together, because it is one rule reaching across both strips.
"""

from __future__ import annotations

import pytest
from conftest import RecordingPlayer
from PySide6.QtGui import QImage
from PySide6.QtWidgets import QApplication
from tray_support import RememberingStore, build, picture, rendered

from stellody.domain.playback import SILENT_VOLUME, RepeatMode
from stellody.shared import resources
from stellody.ui.icons import plain_icon, struck_through
from stellody.ui.main_window import MainWindow
from stellody.ui.settings_keys import (
    FALSE,
    SETTING_MUTED,
    SETTING_REPEAT,
    SETTING_SHUFFLE,
    TRUE,
)
from stellody.ui.toolbar import ICON_PX
from stellody.ui.volume import DEFAULT_PERCENT, MAXIMUM_PERCENT

# Long enough for the walk to come back round to where it started.
RING_WALK = 40
# Written out rather than read from the source it is checking. Comparing the
# constant against itself passes whatever it is changed to, which for a payment
# address is the one change that must never happen quietly.
EXPECTED_DONATE_URL = "https://www.paypal.com/ncp/payment/QGC2XK2Z5WNUW"


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


def _struck() -> QImage:
    """The speaker with the cross over it, composed as the tray composes it."""
    return rendered(
        struck_through(
            resources.unmute_icon_path(), resources.negative_icon_path(), ICON_PX
        )
    )


def _plain() -> QImage:
    """The speaker on its own."""
    return rendered(plain_icon(resources.unmute_icon_path()))


def test_the_two_renderings_are_actually_different(
    application: QApplication,
) -> None:
    """The premise of the test below, so it cannot pass by both being alike."""
    assert _struck() != _plain()


def test_muting_silences_the_device_and_the_speaker_shows_what_a_press_does(
    window: MainWindow, player: RecordingPlayer
) -> None:
    """Struck while the sound is on, since that press is the one that stops it.

    The other way round showed the state, which read as inverted beside the
    view and appearance toggles: both of those name where a press would take
    you, so a picture of where you already are is read the wrong way round.
    """
    button = window._tray.mute_button
    assert picture(button) == _struck(), "sound on, so a press would silence it"
    assert button.toolTip() == "Mute"
    window.toggle_mute()
    assert player.volume == SILENT_VOLUME
    assert button.toolTip() == "Unmute"
    assert picture(button) == _plain(), "silent, so a press would bring it back"
    window.toggle_mute()
    assert player.volume == DEFAULT_PERCENT / MAXIMUM_PERCENT, "back to the level set"
    assert button.toolTip() == "Mute"
    assert picture(button) == _struck()


def test_every_switch_is_written_down_as_it_is_pressed(
    window: MainWindow, store: RememberingStore
) -> None:
    for toggle, key in (
        (window.toggle_mute, SETTING_MUTED),
        (window.toggle_shuffle, SETTING_SHUFFLE),
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
    assert reopened._transport.repeat is RepeatMode.ALBUM
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


def test_the_showing_controls_sit_beside_the_search_that_joins_them(
    window: MainWindow,
) -> None:
    """The view toggle, then the sleeve size, then the equalizer.

    All four change what is on show rather than what is playing, so they sit
    together. Read off the layout as well as off the geometry: a group never
    added to the layout also sits right of search, at nothing, which a
    comparison of positions alone reports as a pass.
    """
    window.show()
    tray = window._tray
    row = tray.layout()
    widgets = [row.itemAt(position).widget() for position in range(row.count())]
    assert tray.showing in widgets, "the group is actually laid out"
    assert widgets.index(tray.showing) == widgets.index(tray.search_box) + 1
    centres = [
        button.mapTo(tray, button.rect().center()).x()
        for button in tray.showing.stops()
    ]
    assert centres == sorted(centres), "view, then size, then the equalizer"
    search = tray.search_button.mapTo(tray, tray.search_button.rect().center()).x()
    assert search < min(centres), "and all three are drawn right of search"


def test_the_view_toggle_says_what_pressing_it_would_do(
    window: MainWindow,
) -> None:
    """A button that names the view on show is read as a state and pressed to
    confirm it, so it names the view it would move to instead."""
    button = window._tray.showing.view_button
    assert button.isEnabled()
    assert not button.icon().isNull(), "it is drawn, not merely reserved"
    window.show_covers(False)
    assert button.toolTip() == "Switch to album art"
    window.show_covers(True)
    assert button.toolTip() == "Switch to the list"


def test_the_view_toggle_is_a_stop_now_that_it_works(
    application: QApplication, window: MainWindow
) -> None:
    """It was named in the ring while disabled so this day needed no reordering."""
    tray = window._tray
    assert tray.showing.view_button in tray.ring_stops()
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
    assert tray.showing.view_button in order, "an enabled control is a stop"
    disabled = window._bottom_tray.repair_button
    assert disabled not in order, "a disabled one still is not"
