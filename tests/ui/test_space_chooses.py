"""Space opens a row, exactly as Enter does, in every view that holds rows.

Oliver's ruling: Enter and Space both play the highlighted track, in the list
and over the sleeves alike. Qt gives that nowhere. Measured before any of this
was written: Enter opened a track in the library while Space did nothing at
all in the same list, because a view spends Space on its selection rather than
on the row under the cursor.

What each view DOES with an opened row is the window's business and is not
restated here; these ask only that the two keys reach the same place.
"""

from __future__ import annotations

import pytest
from library_support import library_window
from PySide6.QtCore import QModelIndex, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication


@pytest.fixture
def window(application: QApplication):
    yield from library_window(application)


def opened_by(view, key: Qt.Key, application: QApplication) -> list[str]:
    """The rows the view reported opening while that key was pressed.

    The listener is taken off again afterwards. Left connected, it goes on
    answering the NEXT press too, which made a second reading arrive in the
    first reading's list before the two were compared.
    """
    seen: list[str] = []
    listener = view.activated.connect(lambda index: seen.append(index.data()))
    try:
        QTest.keyClick(view, key)
        application.processEvents()
    finally:
        view.activated.disconnect(listener)
    return seen


def first_track(window) -> QModelIndex:
    """The first track of the first album, with that album opened."""
    album = window._model.index(0, 0, QModelIndex())
    window._tree.expand(album)
    return window._model.index(0, 0, album)


class TestTheLibraryList:
    def test_space_opens_the_track_enter_opens(
        self, application: QApplication, window
    ) -> None:
        tree = window._tree
        tree.setCurrentIndex(first_track(window))
        tree.setFocus(Qt.FocusReason.TabFocusReason)
        assert opened_by(tree, Qt.Key.Key_Space, application) == opened_by(
            tree, Qt.Key.Key_Return, application
        )

    def test_space_opens_something_at_all(
        self, application: QApplication, window
    ) -> None:
        """Stated separately, so the comparison above cannot pass by both
        keys doing nothing on a day the view stops reporting either.
        """
        tree = window._tree
        tree.setCurrentIndex(first_track(window))
        tree.setFocus(Qt.FocusReason.TabFocusReason)
        assert opened_by(tree, Qt.Key.Key_Space, application)


class TestOverTheSleeves:
    def test_space_opens_what_enter_opens(
        self, application: QApplication, window
    ) -> None:
        grid = window._grid
        grid.setCurrentIndex(window._model.index(0, 0, QModelIndex()))
        grid.setFocus(Qt.FocusReason.TabFocusReason)
        assert opened_by(grid, Qt.Key.Key_Space, application) == opened_by(
            grid, Qt.Key.Key_Return, application
        )

    @pytest.mark.parametrize("key", (Qt.Key.Key_Return, Qt.Key.Key_Space))
    def test_opening_a_sleeve_shows_its_album_in_the_pane(
        self, application: QApplication, window, key: Qt.Key
    ) -> None:
        """Oliver's ruling for the sleeves, where a row is an album.

        Moving the cursor already opens the album under it, so what this
        actually covers is the pane having been shut since, with the cursor
        still standing on that sleeve; there would be no way back to it from
        the keyboard otherwise.
        """
        window.toggle_view()
        grid = window._grid
        sleeve = window._model.index(0, 0, QModelIndex())
        grid.setCurrentIndex(sleeve)
        window.close_album()
        assert window._shown_album is None
        grid.setFocus(Qt.FocusReason.TabFocusReason)
        QTest.keyClick(grid, key)
        application.processEvents()
        assert window._shown_album is not None

    def test_a_track_column_beside_a_sleeve_answers_space(
        self, application: QApplication, window
    ) -> None:
        """The tracks of the open album are their own view, so they need the
        rule as much as the list does; it is where a listener over the
        sleeves actually chooses a track.
        """
        window.toggle_view()
        window.open_album_at(window._model.index(0, 0, QModelIndex()))
        application.processEvents()
        column = window._album_pane.columns[0]
        column.setCurrentIndex(first_track(window))
        column.setFocus(Qt.FocusReason.TabFocusReason)
        assert opened_by(column, Qt.Key.Key_Space, application)


class TestWhereThereIsNothingToOpen:
    def test_a_view_with_no_current_row_is_left_alone(
        self, application: QApplication, window
    ) -> None:
        """Swallowing the key to no effect would be worse than not taking it."""
        tree = window._tree
        tree.setCurrentIndex(QModelIndex())
        tree.setFocus(Qt.FocusReason.TabFocusReason)
        assert opened_by(tree, Qt.Key.Key_Space, application) == []
