"""Typing narrows the library; the track that was hit is pointed at.

The album is kept whole, so what a hit gives is somewhere to look rather than
a shorter album. Selecting the track says where it is and the flash takes the
eye to it, which is the half a test can actually settle: whether a pulse reads
as gentle is not something a headless run can judge.
"""

from __future__ import annotations

import pytest
from conftest import RecordingPlayer
from library_support import PLANETS, SIMPLE, library_window, titles, track
from PySide6.QtCore import QModelIndex, QRect, Qt
from PySide6.QtGui import QColor, QPainter, QPixmap
from PySide6.QtWidgets import QApplication, QStyle, QStyleOptionViewItem
from tray_support import RememberingStore, build

from stellody.domain.album import Album
from stellody.domain.identity import AlbumIdentity
from stellody.ui.covering import RowCover
from stellody.ui.flashing import TURNS
from stellody.ui.row_text import Column
from stellody.ui.theme import palette_for
from stellody.ui.toolbar import SEARCH_BOX_HEIGHT_PX

# A canvas big enough to hold one row and read a pixel out of the middle.
PAINT_PX = 40


@pytest.fixture
def window(application: QApplication):
    yield from library_window(application)


class TestNarrowing:
    def test_the_whole_library_shows_with_nothing_asked(self, window) -> None:
        assert titles(window) == ["The Planets", "Simple Things"]

    def test_an_album_title_narrows_to_that_album(self, window) -> None:
        window.search_changed("simple")
        assert titles(window) == ["Simple Things"]

    def test_an_album_artist_narrows_to_that_album(self, window) -> None:
        window.search_changed("zero 7")
        assert titles(window) == ["Simple Things"]

    def test_a_track_narrows_to_its_album(self, window) -> None:
        window.search_changed("venus")
        assert titles(window) == ["The Planets"]

    def test_the_album_is_kept_whole(self, window) -> None:
        """B: every track stays, so the album reads as it always does."""
        window.search_changed("venus")
        model = window._model
        album = model.index(0, Column.TITLE, QModelIndex())
        assert model.rowCount(album) == PLANETS.track_count

    def test_a_phrase_matching_nothing_empties_the_library(self, window) -> None:
        window.search_changed("saturn")
        assert titles(window) == []

    def test_clearing_brings_everything_back(self, window) -> None:
        window.search_changed("venus")
        window.search_changed("")
        assert titles(window) == ["The Planets", "Simple Things"]

    def test_a_keystroke_leaves_the_sleeves_alone(self, window) -> None:
        """Typing cannot change where a cover is read from.

        Narrowing the art with the albums meant forgetting every cover that
        had been read, so a keystroke sent every visible sleeve back to the
        disk and the pane the search then opened took a placeholder.
        """
        window.search_changed("venus")
        assert set(window._model._art) == {
            PLANETS.identity.art_key,
            SIMPLE.identity.art_key,
        }


class TestPointingAtTheHit:
    def test_the_hit_track_is_selected(self, window) -> None:
        window.search_changed("venus")
        showing = window._model.track_at(window._tree.currentIndex())
        assert showing is not None
        assert showing.title == "Venus"

    def test_the_hit_row_is_painted(self, window) -> None:
        window.search_changed("venus")
        where = window._model.index_for(
            window._model.track_at(window._tree.currentIndex())
        )
        brush = window._model.data(where, Qt.ItemDataRole.BackgroundRole)
        assert brush is not None
        assert brush.color().name() == palette_for(window.theme_mode).found

    def test_another_row_is_not_painted(self, window) -> None:
        window.search_changed("venus")
        album = window._model.index(0, Column.TITLE, QModelIndex())
        assert window._model.data(album, Qt.ItemDataRole.BackgroundRole) is None

    def test_the_flash_gives_up_after_its_turns(self, window) -> None:
        """It is a couple of pulses, not a light left on."""
        window.search_changed("venus")
        flash = window._flash
        assert flash.running
        for _ in range(TURNS):
            flash._turn()
        assert not flash.running
        assert not flash.lit

    def test_an_album_matched_by_name_flashes_nothing(self, window) -> None:
        """Nothing inside it was hit, so there is nothing to point at."""
        window.search_changed("simple")
        assert not window._flash.running

    def test_clearing_stops_the_flash(self, window) -> None:
        window.search_changed("venus")
        window.search_changed("")
        assert not window._flash.running


class TestAskingAgain:
    """Return asks the phrase as it stands, for somebody who has moved off
    what it found. There is nothing else they could type: the box already
    holds the phrase they want, so asking again would mean clearing it.
    """

    def test_return_puts_the_highlight_back_on_the_hit(self, window) -> None:
        window.search_changed("venus")
        window._tree.setCurrentIndex(window._model.index_for(PLANETS.tracks[1]))
        assert window._model.track_at(window._tree.currentIndex()).title == "Mars"
        window.search_again()
        assert window._model.track_at(window._tree.currentIndex()).title == "Venus"

    def test_return_flashes_the_row_again(self, window) -> None:
        """The flash is two pulses and then done, so a second ask relights it."""
        window.search_changed("venus")
        for _ in range(TURNS):
            window._flash._turn()
        assert not window._flash.running
        window.search_again()
        assert window._flash.running

    def test_the_box_asks_it_on_return(self, window) -> None:
        """The wiring itself, since the box is what somebody presses it in."""
        window.toggle_search()
        window._tray.search_box.setText("venus")
        window._tree.setCurrentIndex(window._model.index_for(PLANETS.tracks[1]))
        window._tray.search_box.returnPressed.emit()
        assert window._model.track_at(window._tree.currentIndex()).title == "Venus"

    def test_a_phrase_that_hit_nothing_moves_nothing(self, window) -> None:
        window.search_changed("simple")
        where = window._model.index_for(SIMPLE.tracks[0])
        window._tree.setCurrentIndex(where)
        window.search_again()
        assert window._tree.currentIndex() == where
        assert not window._flash.running

    def test_an_empty_box_points_at_nothing(self, window) -> None:
        """Everything survives, so there is no hit anywhere to be taken to."""
        window.search_again()
        assert not window._flash.running
        assert titles(window) == ["The Planets", "Simple Things"]


class TestTheButton:
    def test_it_opens_and_closes_the_box(self, window) -> None:
        window.toggle_search()
        assert window._tray.searching
        window.toggle_search()
        assert not window._tray.searching

    def test_closing_restores_the_library(self, window) -> None:
        window.toggle_search()
        window._tray.search_box.setText("venus")
        assert titles(window) == ["The Planets"]
        window.toggle_search()
        assert titles(window) == ["The Planets", "Simple Things"]


NEPTUNE = track("Neptune", 1, disc=2)
DOUBLE = Album(
    identity=AlbumIdentity(album_artist="Holst", title="Both Suites"),
    tracks=(track("Venus", 1), NEPTUNE),
)


class TestAMultiDiscAlbum:
    """A disc sits between the album and its tracks, so one expand is not enough."""

    @pytest.fixture
    def window(self, application: QApplication):
        made = build(RememberingStore(), RecordingPlayer())
        made.show_library((DOUBLE,), ())
        application.processEvents()
        yield made
        made.close()

    def test_the_track_really_does_sit_under_a_disc(self, window) -> None:
        """The premise of the fix, stated so the next test cannot pass by luck."""
        where = window._model.index_for(NEPTUNE)
        assert where.isValid()
        assert where.parent().isValid()
        assert where.parent().parent().isValid()

    def test_the_track_ends_up_where_it_can_be_seen(self, window) -> None:
        """The outcome, not the mechanism: a row of no height is a row nobody
        can see, whichever call opened the levels above it."""
        assert window._tree.visualRect(window._model.index_for(NEPTUNE)).height() == 0
        window.search_changed("neptune")
        where = window._model.index_for(NEPTUNE)
        assert window._tree.isExpanded(where.parent())
        assert window._tree.isExpanded(where.parent().parent())
        assert window._tree.visualRect(where).height() > 0

    def test_the_track_is_the_one_selected(self, window) -> None:
        window.search_changed("neptune")
        assert window._model.track_at(window._tree.currentIndex()) is NEPTUNE


class TestHowItLooks:
    def test_the_writing_is_never_repainted(self, window) -> None:
        """The row's colour changes; the text on it does not.

        A flash that repaints the writing put dark text on a dark row in the
        dark appearance, because Qt honours the foreground of a selected row
        while drawing its background from the selection. The colour is
        readable behind the appearance's own text instead.
        """
        window.search_changed("venus")
        where = window._model.index_for(
            window._model.track_at(window._tree.currentIndex())
        )
        assert window._model.data(where, Qt.ItemDataRole.ForegroundRole) is None

    def test_the_box_is_sized_against_the_buttons_beside_it(self, window) -> None:
        assert window._tray.search_box.height() == SEARCH_BOX_HEIGHT_PX


class TestItReallyPaints:
    """Read the pixel back, because a role returned is not a row painted.

    Qt draws a selected row's background from the selection colour and never
    asks the model for `BackgroundRole`. The flash lands on a row a search has
    just selected, which is precisely the case, so the delegate fills it in.
    Nothing short of painting and looking settles whether that works.
    """

    def _painted(self, window, index, selected: bool) -> QColor:
        """The colour the delegate leaves in the middle of one row."""
        delegate = window._tree.itemDelegate()
        option = QStyleOptionViewItem()
        delegate.initStyleOption(option, index)
        option.rect = QRect(0, 0, PAINT_PX, PAINT_PX)
        if selected:
            option.state |= QStyle.StateFlag.State_Selected
        canvas = QPixmap(PAINT_PX, PAINT_PX)
        canvas.fill(QColor("#ff00ff"))
        painter = QPainter(canvas)
        delegate.paint(painter, option, index)
        painter.end()
        return canvas.toImage().pixelColor(PAINT_PX // 2, PAINT_PX - 1)

    def test_a_flashed_row_is_painted_even_while_selected(self, window) -> None:
        window.search_changed("venus")
        where = window._model.index_for(
            window._model.track_at(window._tree.currentIndex())
        )
        painted = self._painted(window, where, selected=True)
        assert painted.name() == palette_for(window.theme_mode).found

    def test_a_row_that_is_not_flashing_is_left_to_the_style(self, window) -> None:
        """Only the flashed row is filled; everything else draws as it always did."""
        window.search_changed("venus")
        other = window._model.index(0, Column.TITLE, QModelIndex())
        assert self._painted(window, other, selected=False).name() != (
            palette_for(window.theme_mode).found
        )

    def test_the_pane_draws_rows_the_same_way(self, window) -> None:
        """One delegate for both views, so a flash cannot differ between them."""
        assert isinstance(window._album_pane.columns[0].itemDelegate(), RowCover)
