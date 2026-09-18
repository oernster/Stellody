"""A track's stars as a column of the library: drawn, pressed and keyed.

Driven through the views themselves rather than by calling the window, since
what is under test is that a press on a drawn star and a number key on a
highlighted row each arrive as a rating of the right track. Whether the stars
read well at this size needs eyes; that they are drawn at all is asserted by
reading a pixel back.
"""

from __future__ import annotations

import pytest
from library_support import ART, PLANETS, SIMPLE
from mouse_support import double_click_at
from PySide6.QtCore import QModelIndex, QPoint, Qt
from PySide6.QtGui import QColor
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from recording_player import RecordingPlayer
from tray_support import RememberingStore, build

from stellody.domain.listening import MAXIMUM_STARS, NO_STARS, track_handle
from stellody.ui.palette import Mode, palette_for
from stellody.ui.row_text import STARS_ROLE, Column
from stellody.ui.star_cells import (
    CELL_MARGIN_PX,
    CELL_STAR_GAP_PX,
    CELL_STAR_PX,
    cell_width,
)
from stellody.ui.theme import HALF

THIRD_STAR = 3
NARROW_TITLE_PX = 120


@pytest.fixture
def window(application: QApplication):
    """A window over a library of two albums, shown as the list."""
    made = build(RememberingStore(), RecordingPlayer())
    made.show_library((PLANETS, SIMPLE), ART)
    made.resize(1200, 700)
    made.show()
    made._tree.expandAll()
    # Room made so the stars are on screen whatever width the window comes up
    # at. Measured coming up 796 wide after another suite's window, which put
    # the stars past the viewport's edge where a press lands on nothing.
    made._tree.setColumnWidth(Column.TITLE, NARROW_TITLE_PX)
    application.processEvents()
    yield made
    made.close()


def _cell(window, row: int, track_row: int) -> QModelIndex:
    """The stars cell of one track row."""
    album = window._model.index(row, Column.TITLE, QModelIndex())
    return window._model.index(track_row, Column.STARS, album)


def _star_point(view, index: QModelIndex, star: int) -> QPoint:
    """The middle of one star in a cell, counting from one, in the viewport.

    Refused when it is off screen, since a press there reaches nothing and a
    test pressing there would fail for a reason that is not the one it names.
    """
    rect = view.visualRect(index)
    left = rect.left() + CELL_MARGIN_PX + (star - 1) * (CELL_STAR_PX + CELL_STAR_GAP_PX)
    point = QPoint(left + CELL_STAR_PX // HALF, rect.center().y())
    assert view.viewport().rect().contains(point), "the star is on screen"
    return point


def _stars(window, row: int = 0, track_row: int = 0) -> int:
    return window._listening.of(
        track_handle((PLANETS, SIMPLE)[row].identity, 1, track_row + 1)
    ).stars


class TestThePointer:
    def test_pressing_the_third_star_rates_the_track_three(self, window) -> None:
        tree = window._tree
        where = _star_point(tree, _cell(window, 0, 0), THIRD_STAR)
        QTest.mouseClick(tree.viewport(), Qt.MouseButton.LeftButton, pos=where)
        assert _stars(window) == THIRD_STAR

    def test_pressing_the_star_it_holds_takes_it_back(self, window) -> None:
        tree = window._tree
        where = _star_point(tree, _cell(window, 0, 0), THIRD_STAR)
        QTest.mouseClick(tree.viewport(), Qt.MouseButton.LeftButton, pos=where)
        QTest.mouseClick(tree.viewport(), Qt.MouseButton.LeftButton, pos=where)
        assert _stars(window) == NO_STARS

    def test_a_press_beside_the_stars_rates_nothing(self, window) -> None:
        tree = window._tree
        title = window._model.index(0, Column.TITLE, _cell(window, 0, 0).parent())
        where = tree.visualRect(title).center()
        QTest.mouseClick(tree.viewport(), Qt.MouseButton.LeftButton, pos=where)
        assert _stars(window) == NO_STARS

    def test_a_double_click_on_the_stars_does_not_start_the_track(self, window) -> None:
        """A double click anywhere else on a row plays it; on the stars it
        would be somebody rating quickly, not asking for music."""
        tree = window._tree
        title = window._model.index(0, Column.TITLE, _cell(window, 0, 0).parent())
        stars = _star_point(tree, _cell(window, 0, 0), THIRD_STAR)
        double_click_at(tree.viewport(), stars)
        assert window._transport.current is None
        double_click_at(tree.viewport(), tree.visualRect(title).center())
        assert window._transport.current is not None, "while the title still plays"

    def test_the_album_under_the_sleeves_takes_a_press_too(
        self, application: QApplication, window
    ) -> None:
        window.toggle_view()
        window.open_album_at(window._model.index(0, Column.TITLE, QModelIndex()))
        application.processEvents()
        column = window._album_pane.columns[0]
        where = _star_point(column, _cell(window, 0, 0), MAXIMUM_STARS)
        QTest.mouseClick(column.viewport(), Qt.MouseButton.LeftButton, pos=where)
        assert _stars(window) == MAXIMUM_STARS


class TestTheNumberKeys:
    def _key(self, view, key: Qt.Key, modifier=Qt.KeyboardModifier.NoModifier):
        view.setFocus(Qt.FocusReason.TabFocusReason)
        QTest.keyClick(view, key, modifier)

    def test_a_number_rates_the_highlighted_track(self, window) -> None:
        tree = window._tree
        tree.setCurrentIndex(_cell(window, 0, 1))
        self._key(tree, Qt.Key.Key_4)
        assert _stars(window, 0, 1) == 4

    def test_nought_clears_it(self, window) -> None:
        tree = window._tree
        cell = _cell(window, 0, 0)
        window.rate_track(cell, THIRD_STAR)
        tree.setCurrentIndex(cell)
        self._key(tree, Qt.Key.Key_0)
        assert _stars(window) == NO_STARS

    def test_the_keypad_counts_as_well(self, window) -> None:
        tree = window._tree
        tree.setCurrentIndex(_cell(window, 0, 0))
        self._key(tree, Qt.Key.Key_5, Qt.KeyboardModifier.KeypadModifier)
        assert _stars(window) == MAXIMUM_STARS

    def test_a_number_on_an_album_row_rates_nothing(self, window) -> None:
        tree = window._tree
        tree.setCurrentIndex(window._model.index(0, Column.TITLE, QModelIndex()))
        self._key(tree, Qt.Key.Key_3)
        assert _stars(window) == NO_STARS

    def test_the_open_album_takes_a_number_too(
        self, application: QApplication, window
    ) -> None:
        window.toggle_view()
        window.open_album_at(window._model.index(1, Column.TITLE, QModelIndex()))
        application.processEvents()
        column = window._album_pane.columns[0]
        self._key(column, Qt.Key.Key_3)
        assert _stars(window, 1, 0) == THIRD_STAR


class TestTheColumn:
    def test_it_is_wide_enough_for_every_star(self, window) -> None:
        assert window._tree.columnWidth(Column.STARS) >= cell_width()

    def test_the_open_album_shows_it(self, window) -> None:
        assert not window._album_pane.columns[0].isColumnHidden(Column.STARS)

    def test_a_rated_track_is_drawn_filled(self, window) -> None:
        """Read back off the screen: the middle of the first star wears the
        star colour once the track is rated; not before."""
        tree = window._tree
        index = _cell(window, 0, 0)
        where = _star_point(tree, index, 1)
        star = QColor(palette_for(window.theme_mode).star).name()

        def colour() -> str:
            return tree.viewport().grab().toImage().pixelColor(where).name()

        assert colour() != star
        window.rate_track(index, 1)
        assert index.data(STARS_ROLE) == 1
        assert colour() == star

    def test_the_stars_follow_the_appearance(self, window) -> None:
        window.show_rating_appearance(Mode.LIGHT)
        for view in (window._tree, *window._album_pane.columns):
            assert view.itemDelegate()._mode is Mode.LIGHT
