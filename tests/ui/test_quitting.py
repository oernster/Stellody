"""Quit has to end the application, not merely close a window.

Measured on the installed build: choosing Quit from the notification area's
menu left Stellody running with no window at all, still holding the tray icon
and the claim to being the copy that runs, so the one control that should have
stopped it could not.

The cause is that quitting when the last window closes is deliberately off,
which is what lets the cross leave Stellody in the tray. Nothing then ends the
event loop unless somebody says so.

The departure is injected rather than reached for, so these tests can watch it
happen without the test run quitting itself.
"""

from __future__ import annotations

import pytest
from conftest import RecordingPlayer
from PySide6.QtWidgets import QApplication
from tray_support import RememberingStore, build

from stellody.ui.close_prompt import CloseAction
from stellody.ui.settings_keys import SETTING_CLOSE


@pytest.fixture
def departures() -> list[str]:
    """Every time the application was asked to end."""
    return []


@pytest.fixture
def window(application: QApplication, departures: list[str]):
    """A window whose departure is recorded rather than taken."""
    store = RememberingStore()
    made = build(store, RecordingPlayer(), leave=lambda: departures.append("left"))
    yield made, store
    made._quitting = True
    made.close()
    made.deleteLater()


def test_the_trays_quit_ends_the_application(window, departures) -> None:
    """The bug: it closed a window nobody could see and left the process up."""
    made, _ = window
    made.quit_application()
    assert departures == ["left"], "Quit has to put the application down"


def test_choosing_quit_at_the_close_prompt_ends_it_too(window, departures) -> None:
    """The other way out, which must mean the same thing."""
    made, store = window
    store.set_setting(SETTING_CLOSE, CloseAction.QUIT.value)
    made.close()
    assert departures == ["left"]


def test_with_no_notification_area_the_cross_ends_the_application(
    window, departures
) -> None:
    """The second door on the same fault; the reason it is one method.

    Staying resident is only honest while there is a tray to come back from.
    Where there is none, which is the case offscreen, closing the window has
    to end Stellody rather than leave a process with nothing on screen at all.

    The opposite path, a visible tray taking the window in, cannot be reached
    here: no platform plugin available to a headless run offers a real
    notification area. It is not claimed to be covered.
    """
    made, store = window
    assert not made.tray_active, "there is no tray in a headless run"
    store.set_setting(SETTING_CLOSE, CloseAction.TRAY.value)
    made.close()
    assert departures == ["left"], "else the process outlives its own window"
