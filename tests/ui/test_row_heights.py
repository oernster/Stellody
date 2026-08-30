"""A row in the list is the height of what is in it.

One pixmap serves both views and it is kept at the size the grid draws it, so
the list was giving every row the height of a sleeve: a line of text sat in a
band four times as tall as it needed. Measured before the change, an album row
was 166 pixels and every track under it was too.

Two things fixed it and both are asserted here. The delegate states the size
of the decoration rather than letting the pixmap state it; rows are no longer
held to one height, since only an album row carries a picture.
"""

from __future__ import annotations

import pytest
from conftest import RecordingPlayer
from PySide6.QtCore import QModelIndex
from PySide6.QtWidgets import QApplication, QStyledItemDelegate
from tray_support import RememberingStore, build

from stellody.ui.covering import GRID_COVER_PX, ROW_COVER_PX
from stellody.ui.models import Column


@pytest.fixture
def window(application: QApplication):
    """A real window holding one album, its tracks on show."""
    made = build(RememberingStore(), RecordingPlayer())
    made.resize(1400, 900)
    made._tree.expandAll()
    yield made
    made.close()


def _album(window) -> QModelIndex:
    """Where the one album sits in the model."""
    return window._model.index(0, Column.TITLE, QModelIndex())


def _track(window) -> QModelIndex:
    """Its first track."""
    return window._model.index(0, Column.TITLE, _album(window))


def _height(window, index) -> int:
    """How tall that row is drawn."""
    return window._tree.visualRect(index).height()


def test_an_album_row_carries_its_sleeve_at_a_rows_size(window) -> None:
    height = _height(window, _album(window))
    assert height >= ROW_COVER_PX, "the cover is still there"
    assert height < GRID_COVER_PX, "but not at the size the grid keeps it"


def test_a_track_row_is_shorter_than_the_album_row(window) -> None:
    """Only a row with a picture in it should be as tall as a picture."""
    assert _height(window, _track(window)) < _height(window, _album(window))


def test_rows_are_not_held_to_one_height(window) -> None:
    """The setting that gave every track the album row's height."""
    assert window._tree.uniformRowHeights() is False


def test_the_delegate_is_what_holds_the_height_down(window) -> None:
    """The guard shown biting: Qt's own delegate brings the tall row back."""
    album = _album(window)
    held = _height(window, album)
    window._tree.setItemDelegate(QStyledItemDelegate(window._tree))
    window._tree.doItemsLayout()
    assert _height(window, album) > held
