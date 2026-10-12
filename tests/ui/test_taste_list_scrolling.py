"""A long taste profiles list scrolls rather than leaving the screen. FR-D95.

Lifted from a button of its own in a host window the height of the screen, so
the room the list opens into is the screen's, which is what decides the bar.
Each overflowing case first asserts its premise: the rows really are taller than
the room, else a bar that never showed would pass for one that was not needed.
"""

from __future__ import annotations

import pytest
from PySide6.QtCore import QPoint, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QPushButton, QWidget

from stellody.domain.taste import TasteProfile
from stellody.ui.lifting import room
from stellody.ui.taste_list import NAME_COLUMN, TasteList

# Far more profiles than an offscreen screen holds; each test checks it is so.
MANY = 60
FEW = 2
# How far up the host window the button sits, so it has a list's room above it.
BUTTON_LIFT_PX = 60


def _profiles(count: int) -> tuple[TasteProfile, ...]:
    return tuple(TasteProfile(f"Profile {n:02d}", ("Jazz",)) for n in range(count))


@pytest.fixture
def lift(application: QApplication):
    """Lift a list of this many profiles; yield it with its button."""
    host = QWidget()
    host.setGeometry(application.primaryScreen().availableGeometry())
    button = QPushButton("Taste profiles", host)
    host.show()
    button.move(0, host.height() - BUTTON_LIFT_PX)
    lists: list[TasteList] = []

    def lifted(count: int) -> tuple[TasteList, QPushButton]:
        taste = TasteList(host, lambda _profile: None, lambda _name: None)
        taste.fill(_profiles(count))
        taste.open_above(button)
        application.processEvents()
        lists.append(taste)
        return taste, button

    yield lifted
    for taste in lists:
        taste.hide()
    host.close()


def _in_view(taste: TasteList, button: QPushButton) -> bool:
    viewport = taste.area.viewport()
    top = button.mapTo(viewport, QPoint(0, 0)).y()
    return top >= 0 and top + button.height() <= viewport.height()


def _press(application: QApplication, key: Qt.Key) -> None:
    QTest.keyClick(application.focusWidget(), key)
    application.processEvents()


class TestTheBar:
    def test_a_list_too_long_for_the_room_scrolls_and_stays_on_screen(
        self, application, lift
    ) -> None:
        taste, button = lift(MANY)
        assert taste.area.widget().sizeHint().height() > room(button), "premise"
        assert taste.area.verticalScrollBar().isVisible()
        screen = application.primaryScreen().availableGeometry()
        assert screen.contains(taste.geometry())

    def test_a_short_list_shows_every_row_and_no_bar(self, application, lift):
        taste, _ = lift(FEW)
        assert not taste.area.verticalScrollBar().isVisible()
        assert all(_in_view(taste, name) for _, name in taste.rows)

    def test_the_scroll_area_is_never_a_stop_on_the_ring(self, lift) -> None:
        """noborderfocus: the rows are the stops, never the pane holding them."""
        taste, _ = lift(MANY)
        assert taste.area.focusPolicy() is Qt.FocusPolicy.NoFocus
        assert taste.area.viewport().focusPolicy() is Qt.FocusPolicy.NoFocus


class TestTheKeyboardFollows:
    def test_up_from_the_first_row_scrolls_the_last_into_view(
        self, application, lift
    ) -> None:
        taste, _ = lift(MANY)
        last = taste.rows[-1][NAME_COLUMN]
        assert not _in_view(taste, last), "premise: the last row starts hidden"
        _press(application, Qt.Key.Key_Up)
        assert application.focusWidget() is last
        assert _in_view(taste, last)

    def test_down_back_to_the_first_row_scrolls_it_into_view(
        self, application, lift
    ) -> None:
        taste, _ = lift(MANY)
        first = taste.rows[0][NAME_COLUMN]
        _press(application, Qt.Key.Key_Up)
        assert not _in_view(taste, first), "premise: wrapping hid the first row"
        _press(application, Qt.Key.Key_Down)
        assert application.focusWidget() is first
        assert _in_view(taste, first)

    def test_shift_tab_from_the_first_row_scrolls_the_last_into_view(
        self, application, lift
    ) -> None:
        taste, _ = lift(MANY)
        _press(application, Qt.Key.Key_Left)
        QTest.keyClick(
            application.focusWidget(),
            Qt.Key.Key_Backtab,
            Qt.KeyboardModifier.ShiftModifier,
        )
        application.processEvents()
        last = taste.rows[-1][NAME_COLUMN]
        assert application.focusWidget() is last
        assert _in_view(taste, last)
