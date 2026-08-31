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

from stellody.ui.close_prompt import CloseAction, ClosePrompt
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


class TestDismissingThePromptDecidesNothing:
    """Reported from the built application: pressing the cross on the close
    prompt minimised the window to the tray. The prompt reported the offered
    default whether or not anybody had chosen it, so being waved away read to
    the caller exactly like choosing Minimise to tray.

    The sharper half of the same fault was never seen, because it is silent:
    dismissing the prompt with the remember box ticked wrote that non-answer
    down as the standing behaviour, so the question never came back.
    """

    def _dismissed(self, tick_remember: bool = False):
        """Stand in for the person pressing the cross on the prompt.

        Through the dialog's own reject, which is where Qt sends the title bar
        cross and Escape alike, rather than through a stub that merely returns
        a code. What is being guarded is what the dialog then reports.
        """

        def press_the_cross(prompt) -> int:
            if tick_remember:
                prompt._remember.setChecked(True)
            prompt.reject()
            return 0

        return press_the_cross

    def test_the_prompt_reports_no_answer_when_it_is_waved_away(self) -> None:
        prompt = ClosePrompt()
        assert not prompt.answered, "nothing is chosen at the moment it opens"
        prompt.reject()
        assert not prompt.answered
        assert prompt.choice is CloseAction.ASK
        prompt.deleteLater()

    def test_either_button_is_an_answer(self) -> None:
        for press, expected in (
            ("_choose_tray", CloseAction.TRAY),
            ("_choose_quit", CloseAction.QUIT),
        ):
            prompt = ClosePrompt()
            getattr(prompt, press)()
            assert prompt.answered
            assert prompt.choice is expected
            prompt.deleteLater()

    def test_the_window_neither_leaves_nor_hides(
        self, window, departures, monkeypatch
    ) -> None:
        """The reported bug: the cross took the window into the tray."""
        made, _ = window
        monkeypatch.setattr(made._notification, "isVisible", lambda: True)
        monkeypatch.setattr(ClosePrompt, "exec", self._dismissed())
        made.show()
        QApplication.processEvents()
        made.close()
        QApplication.processEvents()
        assert made.isVisible(), "the press that opened the prompt is taken back"
        assert departures == [], "nor does it leave"

    def test_a_ticked_remember_box_writes_nothing(self, window, monkeypatch) -> None:
        """The silent half: a non-answer became the standing behaviour."""
        made, store = window
        monkeypatch.setattr(made._notification, "isVisible", lambda: True)
        monkeypatch.setattr(ClosePrompt, "exec", self._dismissed(tick_remember=True))
        made.show()
        made.close()
        assert made.asks_on_close, "the question has to come back"
        # Nothing at all is written, rather than the word for no answer being
        # written down. Storing "ask" would behave the same and would still be
        # a settings key nobody asked for: a dialog waved away leaves no trace.
        assert SETTING_CLOSE not in store.settings
