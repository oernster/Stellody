"""Pressing a sleeve a second time rolls the album pane back up.

The gesture that opened the pane is the one asked to undo it. The pane's own
close button did this from the start, at the size the tray draws its buttons
and wearing the mark the mute switch uses, which is not a way down anybody
found.

Every test here presses the real viewport rather than calling the handler.
That is the whole point: Qt moves the current index during the PRESS, so a
first press on a fresh sleeve and a second press on the open one are told
apart only by reading the press itself. Calling the handler proves nothing
about which of them arrives.
"""

from __future__ import annotations

import pytest
from conftest import RecordingPlayer
from PySide6.QtCore import QModelIndex, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from tray_support import RememberingStore, build, track

from stellody.domain.album import Album
from stellody.domain.identity import AlbumIdentity
from stellody.ui.models import Column

LEFT = Qt.MouseButton.LeftButton


@pytest.fixture
def window(application: QApplication):
    """A real window showing the sleeves of two albums."""
    made = build(RememberingStore(), RecordingPlayer())
    made._model.set_albums(
        (
            Album(
                identity=AlbumIdentity(album_artist="Holst", title="Alpha"),
                tracks=(track(1), track(2)),
            ),
            Album(
                identity=AlbumIdentity(album_artist="Holst", title="Beta"),
                tracks=(track(1), track(2)),
            ),
        )
    )
    made.resize(1400, 900)
    made.show()
    made.toggle_view()
    yield made
    made.close()


def press(window, row: int) -> None:
    """Press the sleeve in that row, as a listener does."""
    where = window._model.index(row, Column.TITLE, QModelIndex())
    QTest.mouseClick(
        window._grid.viewport(), LEFT, pos=window._grid.visualRect(where).center()
    )


class TestPressingASleeveTwice:
    def test_the_first_press_opens_the_pane(self, window) -> None:
        press(window, 0)
        assert window._album_pane.isVisible()
        assert window._album_pane.title.text() == "Alpha"

    def test_the_second_press_rolls_it_back_up(self, window) -> None:
        press(window, 0)
        press(window, 0)
        assert not window._album_pane.isVisible()

    def test_a_third_press_opens_it_again(self, window) -> None:
        """The sleeve used to go dead: it was still current, so nothing changed."""
        press(window, 0)
        press(window, 0)
        press(window, 0)
        assert window._album_pane.isVisible()

    def test_pressing_another_sleeve_switches_rather_than_shuts(self, window) -> None:
        press(window, 0)
        press(window, 1)
        assert window._album_pane.isVisible()
        assert window._album_pane.title.text() == "Beta"

    def test_pressing_past_the_last_sleeve_leaves_the_pane_alone(self, window) -> None:
        """Empty space is not a sleeve, so it says nothing about the pane."""
        press(window, 0)
        QTest.mouseClick(
            window._grid.viewport(), LEFT, pos=window._grid.rect().bottomRight()
        )
        assert window._album_pane.isVisible()


class TestTheOtherWaysDown:
    def test_the_close_button_still_shuts_it(self, window) -> None:
        press(window, 0)
        window._album_pane.close_button.click()
        assert not window._album_pane.isVisible()

    def test_a_sleeve_closed_that_way_opens_on_the_next_press(self, window) -> None:
        press(window, 0)
        window._album_pane.close_button.click()
        press(window, 0)
        assert window._album_pane.isVisible()

    def test_moving_the_selection_still_opens_the_pane(self, window) -> None:
        """Keyboard reach does not go through a press at all."""
        window._grid.setCurrentIndex(
            window._model.index(1, Column.TITLE, QModelIndex())
        )
        assert window._album_pane.isVisible()
        assert window._album_pane.title.text() == "Beta"


class TestTheHighlightIsNotDisturbed:
    def test_reopening_the_album_already_open_leaves_the_choice_alone(
        self, window
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
