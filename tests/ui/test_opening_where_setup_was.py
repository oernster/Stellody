"""A window opened afresh after setup: maximised on the screen setup was on.

Measured on the real platform on 2026-09-13 across four monitors of mixed
scaling: a window laid in a screen's room before it is shown, then marked
maximised, lands maximised on that screen, all four of them. The offscreen
platform has one screen, so these stand screens in front of the window and
check what it asks for; the landing itself rests on that measurement.
"""

from __future__ import annotations

from conftest import RecordingPlayer
from PySide6.QtCore import QRect, Qt
from tray_support import RememberingStore, build

from stellody.ui.geometry import forget_window
from stellody.ui.settings_keys import (
    FALSE,
    SETTING_WINDOW_HEIGHT,
    SETTING_WINDOW_MAXIMISED,
    SETTING_WINDOW_WIDTH,
)

REMEMBERED = {
    SETTING_WINDOW_WIDTH: "1400",
    SETTING_WINDOW_HEIGHT: "900",
    SETTING_WINDOW_MAXIMISED: FALSE,
}
LEFT_NAME = "U13ZA (2)"
LEFT_CORNER = (-4063, 1423)
# Rooms wider than the window's own minimum, so no clamp hides where it went.
LEFT_ROOM = QRect(LEFT_CORNER[0], LEFT_CORNER[1], 2560, 1400)
MAIN_ROOM = QRect(0, 0, 3440, 1392)
NOWHERE = (99999, 99999)


class StandInScreen:
    """Enough of a screen to be chosen and laid out in."""

    def __init__(self, name: str, room: QRect) -> None:
        self._name = name
        self._room = room

    def name(self) -> str:
        return self._name

    def geometry(self) -> QRect:
        return self._room

    def availableGeometry(self) -> QRect:
        return self._room


SCREENS = (
    StandInScreen("LG ULTRAGEAR", MAIN_ROOM),
    StandInScreen(LEFT_NAME, LEFT_ROOM),
)


def _window(store: RememberingStore, monkeypatch=None):
    made = build(store, RecordingPlayer(), leave=lambda: None)
    if monkeypatch is not None:
        monkeypatch.setattr(made, "_screens", lambda: SCREENS)
    return made


def _maximised(made) -> bool:
    return bool(made.windowState() & Qt.WindowState.WindowMaximized)


def test_forgetting_the_window_opens_the_next_one_maximised(application) -> None:
    """What a fresh install, a repair and a reinstall ask of the next launch."""
    store = RememberingStore(REMEMBERED)
    forget_window(store)
    made = _window(store)
    assert _maximised(made)
    made.close()


def test_a_remembered_size_is_honoured_where_nothing_was_forgotten(
    application,
) -> None:
    """The other half of the rule, which a launch after an update relies on."""
    made = _window(RememberingStore(REMEMBERED))
    assert not _maximised(made)
    made.close()


def test_it_opens_in_the_room_of_the_screen_setup_was_on(
    application, monkeypatch
) -> None:
    made = _window(RememberingStore(), monkeypatch)
    assert made.open_on(LEFT_NAME, LEFT_CORNER) is True
    assert made.pos() == LEFT_ROOM.topLeft()
    assert _maximised(made)
    made.close()


def test_a_screen_whose_corner_moved_is_found_by_its_name(
    application, monkeypatch
) -> None:
    made = _window(RememberingStore(), monkeypatch)
    assert made.open_on(LEFT_NAME, NOWHERE) is True
    assert made.pos() == LEFT_ROOM.topLeft()
    made.close()


def test_a_screen_no_longer_attached_leaves_the_window_where_it_was(
    application, monkeypatch
) -> None:
    """Still maximised, on whichever screen Qt chose, as a first run always was."""
    made = _window(RememberingStore(), monkeypatch)
    before = made.pos()
    assert made.open_on("gone", NOWHERE) is False
    assert made.pos() == before
    assert _maximised(made)
    made.close()
