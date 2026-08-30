"""A remembered answer has to be one you can take back.

The close button offers a choice with a box marked remember. Tick it and the
question never returns, which is the point; what was missing is any way to ask
for it again. One tick was permanent; the only route back was to find where
the application keeps its settings and edit them.

It reaches the notification area's menu as well as the window's, because the
window is hidden exactly when somebody most wants the question back.
"""

from __future__ import annotations

import pytest
from conftest import RecordingPlayer
from PySide6.QtWidgets import QApplication
from tray_support import RememberingStore, build

from stellody.ui.close_prompt import CloseAction
from stellody.ui.settings_keys import SETTING_CLOSE


@pytest.fixture
def window(application: QApplication):
    """A window over a store that remembers what it is told."""
    store = RememberingStore()
    made = build(store, RecordingPlayer(), leave=lambda: None)
    yield made, store
    made._quitting = True
    made.close()
    made.deleteLater()


def test_with_nothing_remembered_the_close_button_still_asks(window) -> None:
    made, _ = window
    assert made.asks_on_close, "an unanswered question is the starting state"


def test_a_remembered_answer_is_reported_as_one(window) -> None:
    made, store = window
    store.set_setting(SETTING_CLOSE, CloseAction.TRAY.value)
    assert not made.asks_on_close, "there is something to forget"


def test_forgetting_brings_the_question_back(window) -> None:
    """The whole point: one tick must not be permanent."""
    made, store = window
    store.set_setting(SETTING_CLOSE, CloseAction.QUIT.value)
    assert not made.asks_on_close
    made.forget_close_choice()
    assert made.asks_on_close, "the close button asks again"
    assert store.get_setting(SETTING_CLOSE, "") == CloseAction.ASK.value


def test_forgetting_twice_is_harmless(window) -> None:
    """It is offered from two menus, so it can be reached twice over."""
    made, _ = window
    made.forget_close_choice()
    made.forget_close_choice()
    assert made.asks_on_close


def test_the_offer_to_forget_is_dead_while_there_is_nothing_to_forget(
    window,
) -> None:
    """A control that would do nothing must not look as though it would."""
    made, store = window
    made._show_whether_a_choice_is_remembered()
    assert not made._forget_close_action.isEnabled()
    store.set_setting(SETTING_CLOSE, CloseAction.TRAY.value)
    made._show_whether_a_choice_is_remembered()
    assert made._forget_close_action.isEnabled()
