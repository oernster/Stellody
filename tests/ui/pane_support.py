"""The window the album-pane suites are driven through.

One fixture rather than a copy in each file, since a stand-in window that
drifted between them would have the two suites testing different things while
appearing to test one. The same reason `discovery_wiring_support` exists.
"""

from __future__ import annotations

import pytest
from conftest import RecordingPlayer
from PySide6.QtCore import QEvent, QModelIndex, Qt
from PySide6.QtGui import QFocusEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from tray_support import RememberingStore, build, track

from stellody.domain.album import Album
from stellody.domain.identity import AlbumIdentity
from stellody.ui.row_text import Column

LEFT = Qt.MouseButton.LeftButton
RIGHT = Qt.MouseButton.RightButton


def corners(box) -> tuple[tuple[int, int], ...]:
    """The four corner pixels of a rectangle, clockwise from the top left."""
    return (
        (box.left(), box.top()),
        (box.right(), box.top()),
        (box.left(), box.bottom()),
        (box.right(), box.bottom()),
    )


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


def hand_focus_back(window, reason: Qt.FocusReason) -> None:
    """Give the grid focus the way the toolkit does when something closes."""
    window._grid.clearFocus()
    window._grid.selectionModel().clearCurrentIndex()
    QApplication.processEvents()
    QApplication.sendEvent(window._grid, QFocusEvent(QEvent.Type.FocusIn, reason))
    QApplication.processEvents()


def press(window, row: int, button: Qt.MouseButton = LEFT) -> None:
    """Press the sleeve in that row, as a listener does."""
    where = window._model.index(row, Column.TITLE, QModelIndex())
    QTest.mouseClick(
        window._grid.viewport(),
        button,
        pos=window._grid.visualRect(where).center(),
    )
