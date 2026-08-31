"""The open album's tracks run down two columns rather than one.

What matters here is that two columns are still one library. Both views hold
the same model rooted at the same album; each shows only its own run of rows,
so the order cannot differ between them and no track can go missing between
the foot of one column and the head of the next.
"""

from __future__ import annotations

import pytest
from conftest import RecordingPlayer
from PySide6.QtCore import QModelIndex
from PySide6.QtWidgets import QApplication
from tray_support import RememberingStore, build, track

from stellody.domain.album import Album
from stellody.domain.identity import AlbumIdentity
from stellody.ui.album_pane import TRACK_COLUMNS, AlbumPane, _spans
from stellody.ui.models import AlbumTreeModel
from stellody.ui.row_text import Column


@pytest.fixture
def window(application: QApplication):
    """A real window holding one album of two tracks."""
    made = build(RememberingStore(), RecordingPlayer())
    yield made
    made.close()


def _first_album(window) -> QModelIndex:
    """Where the one album sits in the model."""
    return window._model.index(0, Column.TITLE, QModelIndex())


def _opened(window):
    """The pane, open on the library's one album."""
    window.toggle_view()
    window._grid.setCurrentIndex(_first_album(window))
    return window._album_pane


class TestWhereTheRowsGo:
    """The arithmetic on its own, before any widget is involved."""

    def test_two_columns_are_what_the_pane_runs(self) -> None:
        assert TRACK_COLUMNS == 2

    def test_an_empty_album_asks_for_nothing(self) -> None:
        assert _spans(0) == ((0, 0), (0, 0))

    def test_one_row_leaves_the_second_column_with_none(self) -> None:
        assert _spans(1) == ((0, 1), (1, 1))

    def test_an_even_count_splits_in_half(self) -> None:
        assert _spans(2) == ((0, 1), (1, 2))
        assert _spans(10) == ((0, 5), (5, 10))

    def test_an_odd_count_leaves_the_longer_run_on_the_left(self) -> None:
        """The left is where a reader starts, so the remainder belongs there."""
        assert _spans(5) == ((0, 3), (3, 5))
        assert _spans(9) == ((0, 5), (5, 9))

    def test_every_row_lands_in_exactly_one_column(self) -> None:
        """The property that matters: no track lost between the columns."""
        for rows in range(1, 20):
            landed = [row for start, stop in _spans(rows) for row in range(start, stop)]
            assert landed == list(range(rows)), f"{rows} rows"


class TestTheOpenAlbum:
    def test_each_column_shows_only_its_own_run(self, window) -> None:
        pane = _opened(window)
        where = _first_album(window)
        first, second = pane.columns
        assert not first.isRowHidden(0, where)
        assert first.isRowHidden(1, where)
        assert second.isRowHidden(0, where)
        assert not second.isRowHidden(1, where)

    def test_both_columns_are_the_one_model_on_the_one_album(self, window) -> None:
        pane = _opened(window)
        where = _first_album(window)
        for column in pane.columns:
            assert column.model() is window._model
            assert column.rootIndex() == where

    def test_starting_a_track_from_the_second_column_plays_it(self, window) -> None:
        """Both columns reach the transport, not merely the first."""
        pane = _opened(window)
        where = _first_album(window)
        pane.columns[1].activated.emit(window._model.index(1, Column.TITLE, where))
        assert window._transport.current is not None


class TestAnAlbumTooShortToSplit:
    def test_the_second_column_is_not_drawn_empty(self, application: QApplication):
        """An empty panel beside a full one reads as a fault, so it is hidden."""
        model = AlbumTreeModel()
        model.set_albums(
            (
                Album(
                    identity=AlbumIdentity(album_artist="Holst", title="One"),
                    tracks=(track(1),),
                ),
            )
        )
        pane = AlbumPane(model)
        pane.show_album(
            model.album_at(model.index(0, Column.TITLE, QModelIndex())),
            model.index(0, Column.TITLE, QModelIndex()),
            None,
        )
        assert not pane.columns[1].isVisibleTo(pane)
        pane.deleteLater()
