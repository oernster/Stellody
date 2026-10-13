"""The taste profiles list once lifted: where it sits and the keyboard in it.

FR-D94 for the keyboard. Where it sits is Oliver's ruling of 2026-10-13: flush
with the right edge of the dialog holding the button, at its own width. Built
over the Discover dialog with the helpers `test_taste_profiles` already has.
"""

from __future__ import annotations

import pytest
from PySide6.QtCore import QPoint, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from test_taste_profiles import _JAZZ, _dialog, _store

from stellody.domain.taste import TasteProfile
from stellody.ui.taste_list import NAME_COLUMN


@pytest.fixture
def lifted(application: QApplication):
    dialog = _dialog(_store(TasteProfile("Ambient", ("Ambient",)), *_JAZZ))
    dialog.show()
    dialog.taste.button.click()
    application.processEvents()
    yield dialog, dialog.taste.list.rows
    dialog.taste.list.hide()
    dialog.close()


def _press(application: QApplication, key: Qt.Key) -> None:
    QTest.keyClick(application.focusWidget(), key)
    application.processEvents()


class TestWhereItSits:
    def test_it_lifts_flush_with_the_dialogs_right_edge(
        self, application, lifted
    ) -> None:
        dialog, _ = lifted
        taste = dialog.taste.list
        edge = dialog.mapToGlobal(QPoint(dialog.width(), 0)).x()
        assert taste.geometry().x() + taste.width() == edge

    def test_a_second_lift_keeps_its_width(self, application, lifted) -> None:
        dialog, _ = lifted
        taste = dialog.taste.list
        before = taste.width()
        taste.hide()
        dialog.taste.button.click()
        application.processEvents()
        assert taste.width() == before


class TestTheKeyboard:
    """FR-D94: every button in the list is reached from the keyboard."""

    def test_it_opens_on_the_first_name(self, application, lifted) -> None:
        dialog, rows = lifted
        assert dialog.taste.list.isVisible()
        assert application.focusWidget() is rows[0][NAME_COLUMN]

    def test_up_and_down_keep_the_column_and_wrap(self, application, lifted) -> None:
        _, rows = lifted
        _press(application, Qt.Key.Key_Down)
        assert application.focusWidget() is rows[1][NAME_COLUMN]
        _press(application, Qt.Key.Key_Down)
        assert application.focusWidget() is rows[0][NAME_COLUMN], "wraps"
        _press(application, Qt.Key.Key_Up)
        assert application.focusWidget() is rows[1][NAME_COLUMN], "wraps back"

    def test_left_and_right_cross_between_delete_and_name(
        self, application, lifted
    ) -> None:
        _, rows = lifted
        _press(application, Qt.Key.Key_Left)
        assert application.focusWidget() is rows[0][0]
        _press(application, Qt.Key.Key_Down)
        assert application.focusWidget() is rows[1][0], "the delete column kept"
        _press(application, Qt.Key.Key_Right)
        assert application.focusWidget() is rows[1][NAME_COLUMN]

    def test_tab_walks_every_button_in_reading_order_and_wraps(
        self, application, lifted
    ) -> None:
        _, rows = lifted
        walked = []
        for _ in range(len(rows) * len(rows[0])):
            _press(application, Qt.Key.Key_Tab)
            walked.append(application.focusWidget())
        assert walked == [rows[1][0], rows[1][NAME_COLUMN], rows[0][0], rows[0][1]]

    def test_escape_puts_it_down(self, application, lifted) -> None:
        dialog, _ = lifted
        _press(application, Qt.Key.Key_Escape)
        assert not dialog.taste.list.isVisible()

    def test_choosing_a_name_puts_it_down(self, application, lifted) -> None:
        dialog, rows = lifted
        rows[0][NAME_COLUMN].click()
        assert not dialog.taste.list.isVisible()
        assert dialog.chosen() == ("Ambient",)

    def test_a_second_press_of_the_button_puts_it_down(
        self, application, lifted
    ) -> None:
        dialog, _ = lifted
        dialog.taste.button.click()
        assert not dialog.taste.list.isVisible()
