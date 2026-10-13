"""The whole of a name a tile had to cut short, shown when the pointer rests on it.

A title too long for its tile ends in an ellipsis. Resting the pointer on that
line shows all of it; resting it on a line that fitted shows nothing, because a
tooltip repeating the tile says nothing. The event is sent to a real view
rather than handed to the delegate, so the path a pointer takes is the one
under test.
"""

from __future__ import annotations

import pytest
from PySide6.QtCore import QEvent, QPoint
from PySide6.QtGui import QHelpEvent, QStandardItem, QStandardItemModel
from PySide6.QtWidgets import QApplication, QListView, QToolTip

from stellody.ui.row_text import Column
from stellody.ui.tiles import (
    ARTIST_LINE_PX,
    LINE_GAP_PX,
    NAME_LINE_PX,
    TILE_PAD_PX,
    TITLE_GAP_PX,
    AlbumTile,
    tile_size,
)

SHORT_TITLE = "Faith"
LONG_TITLE = "Listen Without Prejudice Vol. 1, Remastered with Bonus Material"
SHORT_ARTIST = "Holst"
LONG_ARTIST = "The London Symphony Orchestra and Chorus with Guest Soloists"


def _grid(title: str, artist: str) -> QListView:
    """A view over one album, set up as the library grid is."""
    model = QStandardItemModel(0, Column.ARTIST + 1)
    model.appendRow([QStandardItem(title), QStandardItem(artist)])
    view = QListView()
    view.setModel(model)
    view.setModelColumn(Column.TITLE)
    view.setViewMode(QListView.ViewMode.IconMode)
    tiles = AlbumTile(view)
    view.setItemDelegate(tiles)
    view.setGridSize(tile_size(tiles.cover_px))
    view.resize(tile_size(tiles.cover_px) * 2)
    view.show()
    return view


def _title_point(view: QListView) -> QPoint:
    tile = view.visualRect(view.model().index(0, Column.TITLE))
    top = tile.top() + TILE_PAD_PX + view.itemDelegate().cover_px + TITLE_GAP_PX
    return QPoint(tile.center().x(), top + NAME_LINE_PX // 2)


def _artist_point(view: QListView) -> QPoint:
    title = _title_point(view)
    below = NAME_LINE_PX - NAME_LINE_PX // 2 + LINE_GAP_PX + ARTIST_LINE_PX // 2
    return QPoint(title.x(), title.y() + below)


def _rest_on(view: QListView, point: QPoint) -> str:
    """What the tooltip says once the pointer rests at that point."""
    QToolTip.hideText()
    event = QHelpEvent(QEvent.Type.ToolTip, point, view.viewport().mapToGlobal(point))
    QApplication.sendEvent(view.viewport(), event)
    return QToolTip.text() if QToolTip.isVisible() else ""


@pytest.fixture
def made(application: QApplication):
    views = []

    def make(title: str, artist: str) -> QListView:
        view = _grid(title, artist)
        views.append(view)
        return view

    yield make
    QToolTip.hideText()
    for view in views:
        view.close()


class TestACutName:
    def test_a_cut_title_shows_in_full(self, made) -> None:
        view = made(LONG_TITLE, SHORT_ARTIST)
        assert _rest_on(view, _title_point(view)) == LONG_TITLE

    def test_a_cut_artist_shows_in_full(self, made) -> None:
        view = made(SHORT_TITLE, LONG_ARTIST)
        assert _rest_on(view, _artist_point(view)) == LONG_ARTIST

    def test_each_line_answers_for_itself(self, made) -> None:
        """The artist's line shows the artist, never the title above it."""
        view = made(LONG_TITLE, LONG_ARTIST)
        assert _rest_on(view, _title_point(view)) == LONG_TITLE
        assert _rest_on(view, _artist_point(view)) == LONG_ARTIST


class TestANameThatFits:
    def test_a_title_that_fits_shows_nothing(self, made) -> None:
        view = made(SHORT_TITLE, SHORT_ARTIST)
        assert _rest_on(view, _title_point(view)) == ""

    def test_an_artist_that_fits_shows_nothing_beside_a_cut_title(self, made) -> None:
        view = made(LONG_TITLE, SHORT_ARTIST)
        assert _rest_on(view, _artist_point(view)) == ""

    def test_the_sleeve_shows_nothing(self, made) -> None:
        """Only the names say anything; the picture is not a cut line."""
        view = made(LONG_TITLE, LONG_ARTIST)
        tile = view.visualRect(view.model().index(0, Column.TITLE))
        sleeve = QPoint(tile.center().x(), tile.top() + TILE_PAD_PX)
        assert _rest_on(view, sleeve) == ""
