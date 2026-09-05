"""Left and Right as Tab and Shift+Tab, at every stop that does not own them.

The ring is Qt's own focus chain, so Tab already walks it; what is under test
here is the horizontal arrows saying the same thing. Qt spends them elsewhere
by default, differently per control: a slider changes its value with them, a
grid moves its cursor sideways and a button ignores them entirely.

Driven with real key presses at whatever holds the focus, never with
`focusNextChild`: that asks the WINDOW to move focus and never consults the
focused widget, so a walk driven off it would step past a control that answers
the arrows itself and report a pass while proving nothing.
"""

from __future__ import annotations

import contextlib
import pathlib
import tempfile

import pytest
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from stellody.composition import build_window
from stellody.infrastructure.store import SqliteLibraryStore
from stellody.ui.settings_keys import SETTING_ROOT

# How far round the ring a walk is taken before it is called stuck. Comfortably
# more stops than the window has, so a wrap is seen rather than assumed.
A_FULL_LAP = 40


@contextlib.contextmanager
def a_window(application: QApplication):
    """The real window over a throwaway store, pointed at a folder."""
    folder = pathlib.Path(tempfile.mkdtemp())
    store = SqliteLibraryStore(str(folder / "t.sqlite3"))
    store.set_setting(SETTING_ROOT, str(folder))
    made = build_window(store)
    made.show()
    application.processEvents()
    try:
        yield made
    finally:
        made.close()
        store.close()


@pytest.fixture
def window(application: QApplication):
    with a_window(application) as made:
        yield made


def press(application: QApplication, key: Qt.Key) -> None:
    """One key, at whatever currently holds the focus."""
    QTest.keyClick(application.focusWidget(), key)
    application.processEvents()


class TestSteppingTheRing:
    def test_right_moves_the_ring_on(self, application: QApplication, window) -> None:
        first = window._tray.choose_button
        first.setFocus(Qt.FocusReason.TabFocusReason)
        press(application, Qt.Key.Key_Right)
        assert application.focusWidget() is not first

    def test_right_reaches_what_tab_reaches(
        self, application: QApplication, window
    ) -> None:
        """The arrows are the same keys by another name, so the two walks
        cannot be allowed to differ; they are compared rather than described.

        As far as the library list and no further, since that is the one stop
        the two keys are meant to part company at: Right stays there and Tab
        goes on. Everything before it has to agree exactly.
        """

        def walk(key: Qt.Key) -> list[int]:
            window._tray.choose_button.setFocus(Qt.FocusReason.TabFocusReason)
            seen: list[int] = []
            for _ in range(A_FULL_LAP):
                press(application, key)
                if application.focusWidget() is window._tree:
                    return seen
                seen.append(id(application.focusWidget()))
            raise AssertionError(f"{key} never reached the library list")

        walked = walk(Qt.Key.Key_Right)
        assert walked, "the walk moved at all"
        assert walked == walk(Qt.Key.Key_Tab)

    def test_left_steps_back_where_right_came_from(
        self, application: QApplication, window
    ) -> None:
        start = window._tray.choose_button
        start.setFocus(Qt.FocusReason.TabFocusReason)
        press(application, Qt.Key.Key_Right)
        assert application.focusWidget() is not start
        press(application, Qt.Key.Key_Left)
        assert application.focusWidget() is start

    def test_the_ring_wraps_rather_than_ending(
        self, application: QApplication, window
    ) -> None:
        """A dead end at either end would leave a stop unreachable."""
        start = window._tray.choose_button
        start.setFocus(Qt.FocusReason.TabFocusReason)
        for _ in range(A_FULL_LAP):
            press(application, Qt.Key.Key_Tab)
            if application.focusWidget() is start:
                return
        raise AssertionError("the ring never came back round")


class TestWhatOwnsTheArrows:
    def test_the_library_list_keeps_them(
        self, application: QApplication, window
    ) -> None:
        """Oliver's one stated exception: Left and Right shut and open an
        album there, which is the only keyboard route into one. Tab is still
        the way out, so nothing is trapped.
        """
        tree = window._tree
        tree.setFocus(Qt.FocusReason.TabFocusReason)
        press(application, Qt.Key.Key_Right)
        assert application.focusWidget() is tree
        press(application, Qt.Key.Key_Tab)
        assert application.focusWidget() is not tree

    def test_a_key_a_stop_declined_is_not_answered_for_the_pane_behind_it(
        self, application: QApplication, window
    ) -> None:
        """A key nobody consumes is offered to the parent, then to ITS parent.

        Measured: a Right the library list had declined arrived a second time
        addressed to the stack behind it; the ring then stepped from there and
        landed on the menu bar. So the offer is answered only where the
        receiver is the stop the keyboard is actually on.
        """
        tree = window._tree
        tree.setFocus(Qt.FocusReason.TabFocusReason)
        behind = tree.parentWidget()
        QTest.keyClick(behind, Qt.Key.Key_Right)
        application.processEvents()
        assert window.focusWidget() is tree

    def test_a_text_field_keeps_them_for_its_caret(
        self, application: QApplication, window
    ) -> None:
        """A field is left with Tab as the way out, which is the model's
        seventh invariant; taking the arrows would take the caret with them.
        """
        box = window._tray.search_box
        box.setVisible(True)
        box.setText("abc")
        box.setFocus(Qt.FocusReason.TabFocusReason)
        press(application, Qt.Key.Key_Left)
        assert application.focusWidget() is box

    def test_the_menu_bar_keeps_them_for_its_own_titles(
        self, application: QApplication, window
    ) -> None:
        bar = window.menuBar()
        window.focusNextChild()
        assert application.focusWidget() is bar
        press(application, Qt.Key.Key_Right)
        assert bar.cursor_at == 1, "the bar walked its own titles"


class TestTheSliders:
    def test_up_and_down_move_the_position(
        self, application: QApplication, window
    ) -> None:
        """Oliver's ruling: the vertical keys change the value once the
        slider is focused; the horizontal ones move the ring on.
        """
        slider = window._position_bar.slider
        slider.setEnabled(True)
        slider.setValue(slider.maximum() // 2)
        slider.setFocus(Qt.FocusReason.TabFocusReason)
        was = slider.value()
        press(application, Qt.Key.Key_Up)
        assert slider.value() > was
        press(application, Qt.Key.Key_Down)
        assert slider.value() == was

    def test_right_leaves_the_position_alone_and_moves_on(
        self, application: QApplication, window
    ) -> None:
        """Qt spends Left and Right on a horizontal slider's value, which is
        exactly what the ring wants them for, so this is the case that would
        silently seek the track if the rule were ever dropped.
        """
        slider = window._position_bar.slider
        slider.setEnabled(True)
        slider.setValue(slider.maximum() // 2)
        slider.setFocus(Qt.FocusReason.TabFocusReason)
        was = slider.value()
        press(application, Qt.Key.Key_Right)
        assert slider.value() == was
        assert application.focusWidget() is not slider

    def test_the_volume_opens_changes_and_is_left_by_the_arrows(
        self, application: QApplication, window
    ) -> None:
        """The whole keyboard route to the volume, end to end.

        The slider lives in a popup, so it is on no ring at all; the button
        that opens it is the stop the ring is really standing on. Leaving with
        an arrow therefore has to shut the popup as it goes, else the ring
        would be reaching for a neighbour the slider does not have.
        """
        tray = window._tray
        button = tray.volume_button
        button.setFocus(Qt.FocusReason.TabFocusReason)
        press(application, Qt.Key.Key_Space)
        slider = tray._popup.slider
        assert application.focusWidget() is slider
        was = slider.value()
        press(application, Qt.Key.Key_Down)
        assert slider.value() < was
        press(application, Qt.Key.Key_Right)
        assert application.activePopupWidget() is None
        assert application.focusWidget() is tray.mute_button
