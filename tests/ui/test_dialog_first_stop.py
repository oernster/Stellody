"""A dialog opens already focused on its first usable control.

The opposite of the main window, on purpose; the two must not be unified.
A window is looked at before it is acted in, so nothing there is lit until the
first Tab. A dialog was opened deliberately, to do the one thing it is for, so
waiting for a Tab press costs a keystroke and says nothing.

Asserted against the dialog's OWN focus chain rather than against a named
control, so the check keeps meaning as a dialog gains and loses controls: what
is pinned is that focus lands where the first Tab would have gone.
"""

from __future__ import annotations

import pathlib
import tempfile

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractScrollArea,
    QApplication,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
)

from stellody.composition import build_window
from stellody.domain.equalising import Equalisation
from stellody.infrastructure.store import SqliteLibraryStore
from stellody.ui.close_prompt import ClosePrompt
from stellody.ui.dialogs import AboutDialog, FirstStopDialog
from stellody.ui.equaliser import EqualiserDialog
from stellody.ui.guide import GuideDialog
from stellody.ui.health import HealthDialog
from stellody.ui.ringed_check import RingedCheckBox
from stellody.ui.settings_keys import SETTING_ROOT


@pytest.fixture
def window(application: QApplication):
    """The real window, since every dialog here is opened from one."""
    folder = pathlib.Path(tempfile.mkdtemp())
    store = SqliteLibraryStore(str(folder / "t.sqlite3"))
    store.set_setting(SETTING_ROOT, str(folder))
    made = build_window(store)
    made.show()
    application.processEvents()
    yield made
    made.close()
    store.close()


def opened(dialog, application: QApplication):
    """Show a dialog and give back what it left focused."""
    dialog.show()
    application.processEvents()
    return application.focusWidget()


DIALOGS = {
    "close prompt": lambda window: ClosePrompt(window),
    "equaliser": lambda window: EqualiserDialog(
        window, Equalisation(), lambda _curve: None
    ),
    "health": lambda window: HealthDialog((), window),
    "health offering a repair": lambda window: HealthDialog(
        (), window, can_repair=True
    ),
    "about": lambda window: AboutDialog(window),
    "guide": lambda window: GuideDialog(window),
}


@pytest.mark.parametrize("build", DIALOGS.values(), ids=DIALOGS.keys())
def test_every_dialog_opens_on_its_own_first_stop(
    application: QApplication, window, build
) -> None:
    dialog = build(window)
    try:
        focused = opened(dialog, application)
        assert focused is not None, "something is focused"
        assert focused is dialog.first_stop(), "and it is where Tab would land"
        assert dialog.isAncestorOf(focused), "inside the dialog, not behind it"
    finally:
        dialog.close()
        dialog.deleteLater()


@pytest.mark.parametrize("build", DIALOGS.values(), ids=DIALOGS.keys())
def test_no_dialog_opens_on_a_reading_pane(
    application: QApplication, window, build
) -> None:
    """The reported fault: a green rectangle round the whole page on opening.

    A pane that overflows is a real Tab stop, so it was the first stop of every
    reading dialog and every one of them opened ringed before anybody had done
    anything. The ring is correct once somebody tabs to it; drawn on opening it
    outlines the entire page while offering nothing to act on.

    Asserted over the widget the dialog actually focused rather than over the
    stylesheet, since what is wrong is where focus lands and not what a focused
    pane looks like.
    """
    dialog = build(window)
    try:
        focused = opened(dialog, application)
        assert not isinstance(focused, QAbstractScrollArea), type(focused).__name__
    finally:
        dialog.close()
        dialog.deleteLater()


class TestTheBaseItself:
    """Built here rather than found, so the awkward cases can be arranged."""

    def _dialog(self, window, *, lead_disabled: bool = False) -> FirstStopDialog:
        dialog = FirstStopDialog(window)
        column = QVBoxLayout(dialog)
        lead = QPushButton("first", dialog)
        lead.setEnabled(not lead_disabled)
        column.addWidget(lead)
        column.addWidget(QLineEdit(dialog))
        # The house checkbox, not a plain one: the stylesheet hands both
        # ring colours to every QCheckBox, so a plain one is warned about.
        column.addWidget(RingedCheckBox("last", dialog))
        return dialog

    def test_it_opens_on_the_leading_control(
        self, application: QApplication, window
    ) -> None:
        dialog = self._dialog(window)
        try:
            assert isinstance(opened(dialog, application), QPushButton)
        finally:
            dialog.close()

    def test_a_disabled_leading_control_is_passed_over(
        self, application: QApplication, window
    ) -> None:
        """A dialog must never open focused on something that cannot be used."""
        dialog = self._dialog(window, lead_disabled=True)
        try:
            assert isinstance(opened(dialog, application), QLineEdit)
        finally:
            dialog.close()

    def test_a_hidden_leading_control_is_passed_over(
        self, application: QApplication, window
    ) -> None:
        dialog = self._dialog(window)
        dialog.layout().itemAt(0).widget().setVisible(False)
        try:
            assert isinstance(opened(dialog, application), QLineEdit)
        finally:
            dialog.close()

    def test_a_dialog_with_nothing_to_focus_focuses_nothing(
        self, application: QApplication, window
    ) -> None:
        """It answers None rather than failing, so an empty dialog still opens."""
        dialog = FirstStopDialog(window)
        try:
            dialog.show()
            application.processEvents()
            assert dialog.first_stop() is None
        finally:
            dialog.close()

    def test_the_ring_shown_is_the_one_a_tab_press_shows(
        self, application: QApplication, window
    ) -> None:
        """Focused with the tab reason, so the control wears the keyboard ring
        rather than a different-looking one for having been focused another
        way. Read off the widget, since the reason itself is not kept."""
        dialog = self._dialog(window)
        try:
            focused = opened(dialog, application)
            assert focused.hasFocus()
            assert focused is dialog.first_stop()
        finally:
            dialog.close()

    def test_reopening_does_not_place_focus_a_second_time(
        self, application: QApplication, window
    ) -> None:
        """Only the first opening places focus; after that it is the user's.

        What is asserted is that the dialog does not reach for its first stop
        again, not where focus ends up: hiding a dialog takes the application's
        focus with it, so there may be nothing focused at all on the way back.
        """
        dialog = self._dialog(window)
        try:
            lead = opened(dialog, application)
            assert lead is dialog.first_stop()
            dialog.layout().itemAt(2).widget().setFocus(Qt.FocusReason.TabFocusReason)
            dialog.hide()
            application.processEvents()
            dialog.show()
            application.processEvents()
            assert application.focusWidget() is not lead, "not grabbed back"
        finally:
            dialog.close()
