"""Maximising lands on the screen the title bar is on.

The fault itself belongs to the real platform: the offscreen one has no title
bar, no monitors of differing scaling and no Windows deciding where a maximise
goes. What is held here is the decision and the move. The Windows half was
proved with real mouse input on the machine it was reported from, which
ARCHITECTURE.md records.
"""

from __future__ import annotations

import ctypes
import sys

import pytest
from conftest import RecordingPlayer
from PySide6.QtCore import QByteArray, QRect, QSize
from tray_support import RememberingStore, build

from stellody.ui.geometry import Geometry
from stellody.ui.maximising import Maximising, screen_at
from stellody.ui.settings_keys import SETTING_WINDOW_HEIGHT, SETTING_WINDOW_WIDTH

ON_WINDOWS = sys.platform == "win32"
only_on_windows = pytest.mark.skipif(not ON_WINDOWS, reason="a Windows message")

ROOMY = QRect(0, 0, 2560, 1440)
# Smaller than the window this module builds, so the bounding can be seen.
ELSEWHERE = QRect(100, 50, 1500, 800)
# From WinUser.h: a system command that is not a maximise and a message that is
# not a system command at all.
SC_MINIMIZE = 0xF020
WM_SIZE = 0x0005
# The low bits Windows adds to a system command for its own use.
WINDOWS_OWN_BITS = 0x0002


class StandInScreen:
    """A screen with a place and a size, which is all a maximise asks of one."""

    def __init__(self, room: QRect) -> None:
        self._room = room

    def geometry(self) -> QRect:
        """Where the screen is."""
        return self._room

    def availableGeometry(self) -> QRect:
        """The room a window may take on it."""
        return self._room


@pytest.fixture
def window(application, monkeypatch: pytest.MonkeyPatch):
    """A shown window at 1600 by 910, with room enough that nothing is clamped."""
    monkeypatch.setattr(Geometry, "_usable_screen", lambda self: StandInScreen(ROOMY))
    store = RememberingStore(
        {SETTING_WINDOW_WIDTH: "1600", SETTING_WINDOW_HEIGHT: "910"}
    )
    made = build(store, RecordingPlayer(), leave=lambda: None)
    made.show()
    application.processEvents()
    yield made
    made.close()


def title_bar_on(monkeypatch: pytest.MonkeyPatch, screen) -> None:
    """Say which screen the title bar is on, which offscreen cannot say."""
    monkeypatch.setattr(Maximising, "_title_bar_screen", lambda self: screen)


class TestWhichScreen:
    def test_the_screen_is_found_by_its_corner(self) -> None:
        wanted = StandInScreen(QRect(-223, 1440, 1536, 960))
        other = StandInScreen(QRect(0, 0, 3440, 1440))
        assert screen_at((-223, 1440), [other, wanted]) is wanted

    def test_a_corner_nothing_sits_at_finds_nothing(self) -> None:
        assert screen_at((7, 7), [StandInScreen(ROOMY)]) is None


class TestTheMove:
    def test_a_title_bar_elsewhere_maximises_there(
        self, application, window, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The reported fault: the maximise goes where the title bar is."""
        title_bar_on(monkeypatch, StandInScreen(ELSEWHERE))
        assert window.maximise_where_the_title_bar_is()
        application.processEvents()
        assert window.isMaximized()
        # Contained rather than equal: `move` places the frame, which the
        # offscreen platform draws two pixels wide, while this is the content.
        assert ELSEWHERE.contains(window.normalGeometry().topLeft())

    def test_the_size_to_restore_to_is_kept_where_it_fits(
        self, application, window, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Bounded by the new screen's room rather than replaced by it."""
        title_bar_on(monkeypatch, StandInScreen(ELSEWHERE))
        window.maximise_where_the_title_bar_is()
        application.processEvents()
        assert window.normalGeometry().size() == QSize(1500, 800)

    def test_a_title_bar_on_the_same_screen_is_left_to_windows(
        self, application, window, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Where Windows already agrees, nothing here takes the command."""
        title_bar_on(monkeypatch, window.screen())
        assert not window.maximise_where_the_title_bar_is()
        application.processEvents()
        assert not window.isMaximized()

    def test_a_title_bar_nobody_can_place_is_left_to_windows(
        self, application, window, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        title_bar_on(monkeypatch, None)
        assert not window.maximise_where_the_title_bar_is()
        application.processEvents()
        assert not window.isMaximized()


def windows_message(kind: int, command: int):
    """A MSG as Qt hands one over, kept alive by the caller."""
    from ctypes import wintypes

    message = wintypes.MSG()
    message.message = kind
    message.wParam = command
    return message


@only_on_windows
class TestTheMessage:
    def test_a_maximise_is_recognised_whatever_its_low_bits(self) -> None:
        """A double click on a title bar carries bits Windows keeps for itself."""
        from stellody.ui import title_bar

        message = windows_message(
            title_bar.WM_SYSCOMMAND, title_bar.SC_MAXIMIZE | WINDOWS_OWN_BITS
        )
        address = ctypes.addressof(message)
        assert title_bar.is_maximise_command(title_bar.WINDOWS_MESSAGE, address)

    def test_another_system_command_is_not(self) -> None:
        from stellody.ui import title_bar

        message = windows_message(title_bar.WM_SYSCOMMAND, SC_MINIMIZE)
        address = ctypes.addressof(message)
        assert not title_bar.is_maximise_command(title_bar.WINDOWS_MESSAGE, address)

    def test_another_message_is_not(self) -> None:
        from stellody.ui import title_bar

        message = windows_message(WM_SIZE, title_bar.SC_MAXIMIZE)
        address = ctypes.addressof(message)
        assert not title_bar.is_maximise_command(title_bar.WINDOWS_MESSAGE, address)

    def test_a_message_from_another_platform_is_not(self) -> None:
        from stellody.ui import title_bar

        message = windows_message(title_bar.WM_SYSCOMMAND, title_bar.SC_MAXIMIZE)
        address = ctypes.addressof(message)
        assert not title_bar.is_maximise_command(b"xcb_generic_event_t", address)

    def test_the_window_takes_a_maximise_bound_elsewhere(
        self, application, window, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The whole route, from the message Qt offers to the window maximised."""
        from stellody.ui import title_bar

        title_bar_on(monkeypatch, StandInScreen(ELSEWHERE))
        message = windows_message(title_bar.WM_SYSCOMMAND, title_bar.SC_MAXIMIZE)
        handled = window.nativeEvent(
            QByteArray(title_bar.WINDOWS_MESSAGE), ctypes.addressof(message)
        )
        application.processEvents()
        assert handled == (True, 0)
        assert window.isMaximized()

    def test_anything_else_is_passed_on_untouched(self) -> None:
        """Handed to the base class exactly as it arrived.

        Stated over a stand-in base rather than the real window: Qt's own
        handler refuses an address that did not come from Qt.
        """
        from stellody.ui import title_bar

        class PassedOn:
            def nativeEvent(self, event_type, message):
                return ("passed on", bytes(event_type), message)

        class Probe(Maximising, PassedOn):
            pass

        message = windows_message(WM_SIZE, 0)
        address = ctypes.addressof(message)
        answer = Probe().nativeEvent(QByteArray(title_bar.WINDOWS_MESSAGE), address)
        assert answer == ("passed on", title_bar.WINDOWS_MESSAGE, address)
