"""Pressing a sleeve a second time rolls the album pane back up.

The gesture that opened the pane is the one asked to undo it. The pane's own
close button did this from the start, at the size the tray draws its buttons,
which is not a way down anybody found.

What the pane LOOKS like is `test_the_pane_looks_right`; this file is about
what a press does.

Every test here presses the real viewport rather than calling the handler.
That is the whole point: Qt moves the current index during the PRESS, so a
first press on a fresh sleeve and a second press on the open one are told
apart only by reading the press itself. Calling the handler proves nothing
about which of them arrives.
"""

from __future__ import annotations

import pytest
from pane_support import LEFT, RIGHT, hand_focus_back, press, window
from PySide6.QtCore import QEvent, QModelIndex, Qt
from PySide6.QtGui import QFocusEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from stellody.ui.main_window import MainWindow
from stellody.ui.row_text import Column

# The fixture is imported for pytest to find, so it is re-exported rather
# than left looking unused.
__all__ = ["window"]


class TestPressingASleeveTwice:
    def test_the_first_press_opens_the_pane(self, window: MainWindow) -> None:
        press(window, 0)
        assert window._album_pane.isVisible()
        assert window._album_pane.title.text() == "Alpha"

    def test_the_second_press_rolls_it_back_up(self, window: MainWindow) -> None:
        press(window, 0)
        press(window, 0)
        assert not window._album_pane.isVisible()

    def test_a_third_press_opens_it_again(self, window: MainWindow) -> None:
        """The sleeve used to go dead: it was still current, so nothing changed."""
        press(window, 0)
        press(window, 0)
        press(window, 0)
        assert window._album_pane.isVisible()

    def test_pressing_another_sleeve_switches_rather_than_shuts(
        self, window: MainWindow
    ) -> None:
        press(window, 0)
        press(window, 1)
        assert window._album_pane.isVisible()
        assert window._album_pane.title.text() == "Beta"

    def test_pressing_past_the_last_sleeve_leaves_the_pane_alone(
        self, window: MainWindow
    ) -> None:
        """Empty space is not a sleeve, so it says nothing about the pane."""
        press(window, 0)
        QTest.mouseClick(
            window._grid.viewport(), LEFT, pos=window._grid.rect().bottomRight()
        )
        assert window._album_pane.isVisible()


class TestTheOtherWaysDown:
    def test_the_close_button_still_shuts_it(self, window: MainWindow) -> None:
        press(window, 0)
        window._album_pane.close_button.click()
        assert not window._album_pane.isVisible()

    def test_a_sleeve_closed_that_way_opens_on_the_next_press(
        self, window: MainWindow
    ) -> None:
        press(window, 0)
        window._album_pane.close_button.click()
        press(window, 0)
        assert window._album_pane.isVisible()

    def test_moving_the_selection_still_opens_the_pane(
        self, window: MainWindow
    ) -> None:
        """Keyboard reach does not go through a press at all."""
        window._grid.setCurrentIndex(
            window._model.index(1, Column.TITLE, QModelIndex())
        )
        assert window._album_pane.isVisible()
        assert window._album_pane.title.text() == "Beta"


class TestTheHighlightIsNotDisturbed:
    def test_reopening_the_album_already_open_leaves_the_choice_alone(
        self, window: MainWindow
    ) -> None:
        """A press and the selection change it causes both ask to open it."""
        press(window, 0)
        pane = window._album_pane
        album = window._model.album_at(
            window._model.index(0, Column.TITLE, QModelIndex())
        )
        second = window._model.index_for(album.ordered_tracks()[1])
        pane.columns[1].setCurrentIndex(second)
        window.open_album_at(window._model.index(0, Column.TITLE, QModelIndex()))
        assert window._model.track_at(pane.current_index()).track_number == 2


class TestTheRightButtonLeavesThePaneAlone:
    """A right press is somebody reaching for the sleeve's menu.

    Rolling the pane up under them takes away the album they are pointing at
    as they point at it, which is what it did: the press filter read every
    button rather than the left one.
    """

    def test_a_right_press_on_the_open_sleeve_keeps_it_open(
        self, window: MainWindow
    ) -> None:
        press(window, 0)
        press(window, 0, RIGHT)
        assert window._album_pane.isVisible()
        assert window._album_pane.title.text() == "Alpha"

    def test_a_left_press_still_rolls_it_up_afterwards(
        self, window: MainWindow
    ) -> None:
        """The right press must not have consumed the gesture either."""
        press(window, 0)
        press(window, 0, RIGHT)
        press(window, 0)
        assert not window._album_pane.isVisible()

    def test_a_right_press_on_another_sleeve_leaves_the_open_one(
        self, window: MainWindow
    ) -> None:
        """Reaching for a menu is not asking to see a different album."""
        press(window, 0)
        press(window, 1, RIGHT)
        assert window._album_pane.isVisible()
        assert window._album_pane.title.text() == "Alpha"

    def test_a_right_press_on_a_shut_pane_leaves_it_shut(
        self, window: MainWindow
    ) -> None:
        """Nothing was on show, so the menu brings nothing out with it."""
        press(window, 0, RIGHT)
        assert not window._album_pane.isVisible()

    def test_a_right_press_never_opens_and_shuts_in_one(
        self, window: MainWindow
    ) -> None:
        """Two right presses in a row are still not a toggle."""
        press(window, 0)
        press(window, 0, RIGHT)
        press(window, 0, RIGHT)
        assert window._album_pane.isVisible()


class TestBeingHandedFocusBackLeavesThePlaceAlone:
    """What the right press exposed, one step further along.

    A view holding no current item gives the place to its first one as soon as
    focus arrives by any route other than the mouse. The right press is taken
    and dropped, so no sleeve is current; whatever that press opens then takes
    focus. Handing it back put the place on the top of the library. In the
    built application that read as the first album highlighting itself, with
    its pane opening, while the sleeve actually pointed at was left alone.

    Two ways out were met in turn, a menu and then the tag editor, so the
    reasons are asked about by name here. The platform's own window activation
    cannot be raised offscreen, which is why each is sent rather than staged:
    a dialog hands focus back as ActiveWindow and a menu as Popup. Both were
    measured inventing row 0 before this was fixed.
    """

    def _menu_and_back(self, window, row: int) -> None:
        """Right press a sleeve, take the menu it asks for, then dismiss it."""
        press(window, row, RIGHT)
        window.show_transport_menu(
            window._grid.visualRect(
                window._model.index(row, Column.TITLE, QModelIndex())
            ).center(),
            window._grid,
        )
        window._menu.close()
        QApplication.sendEvent(
            window._grid,
            QFocusEvent(QEvent.Type.FocusIn, Qt.FocusReason.PopupFocusReason),
        )
        QApplication.processEvents()

    def test_the_first_sleeve_is_not_given_the_place(self, window: MainWindow) -> None:
        self._menu_and_back(window, 1)
        assert not window._grid.currentIndex().isValid()

    def test_the_pane_stays_shut(self, window: MainWindow) -> None:
        """The invented place opened an album nobody chose."""
        self._menu_and_back(window, 1)
        assert not window._album_pane.isVisible()

    def test_the_left_press_after_it_opens_what_it_lands_on(
        self, window: MainWindow
    ) -> None:
        self._menu_and_back(window, 1)
        press(window, 1)
        assert window._album_pane.isVisible()
        assert window._album_pane.title.text() == "Beta"

    @pytest.mark.parametrize(
        "reason",
        (
            Qt.FocusReason.PopupFocusReason,
            Qt.FocusReason.ActiveWindowFocusReason,
            Qt.FocusReason.OtherFocusReason,
        ),
        ids=("a menu closing", "a dialog closing", "anything else"),
    )
    def test_no_way_of_being_handed_focus_takes_a_sleeve(self, window, reason) -> None:
        """The rule is the ways in that ARE a choice, not a list of doors."""
        hand_focus_back(window, reason)
        assert not window._grid.currentIndex().isValid()
        assert not window._album_pane.isVisible()

    @pytest.mark.parametrize(
        "reason",
        (Qt.FocusReason.TabFocusReason, Qt.FocusReason.BacktabFocusReason),
        ids=("tab", "shift tab"),
    )
    def test_focus_arriving_by_keyboard_still_finds_a_sleeve(
        self, window, reason
    ) -> None:
        """Reaching the grid by key is asking for a place in it, which is the
        one arrival that still gets one."""
        hand_focus_back(window, reason)
        assert window._grid.currentIndex().isValid()
