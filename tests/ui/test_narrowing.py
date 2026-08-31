"""Typing narrows the library; the track that was hit is pointed at.

The album is kept whole, so what a hit gives is somewhere to look rather than
a shorter album. Selecting the track says where it is and the flash takes the
eye to it, which is the half a test can actually settle: whether a pulse reads
as gentle is not something a headless run can judge.
"""

from __future__ import annotations

import pytest
from conftest import RecordingPlayer
from PySide6.QtCore import QModelIndex, QRect, Qt
from PySide6.QtGui import QColor, QPainter, QPixmap
from PySide6.QtWidgets import QApplication, QStyle, QStyleOptionViewItem
from tray_support import RememberingStore, build

from stellody.application.artwork import AlbumArtSources
from stellody.domain.album import Album
from stellody.domain.identity import AlbumIdentity
from stellody.domain.track import CD_SAMPLE_RATE, Track, TrackSource
from stellody.ui.covering import RowCover
from stellody.ui.flashing import TURNS
from stellody.ui.models import Column
from stellody.ui.theme import palette_for
from stellody.ui.toolbar import SEARCH_BOX_HEIGHT_PX

# A canvas big enough to hold one row and read a pixel out of the middle.
PAINT_PX = 40


def _track(title: str, number: int, disc: int = 1) -> Track:
    """One track carrying a real title, since a title is what is searched."""
    return Track(
        source=TrackSource(path=f"{number:02d} {title}.flac"),
        disc_number=disc,
        track_number=number,
        title=title,
        artists=("Holst",),
        duration_ms=1000,
        sample_rate=CD_SAMPLE_RATE,
        bit_depth=16,
    )


PLANETS = Album(
    identity=AlbumIdentity(album_artist="Holst", title="The Planets"),
    tracks=(_track("Venus", 1), _track("Mars", 2)),
)
SIMPLE = Album(
    identity=AlbumIdentity(album_artist="Zero 7", title="Simple Things"),
    tracks=(_track("Destiny", 1),),
)
ART = (
    AlbumArtSources(key=PLANETS.identity.art_key, sidecars=("planets.jpg",)),
    AlbumArtSources(key=SIMPLE.identity.art_key, sidecars=("simple.jpg",)),
)


@pytest.fixture
def window(application: QApplication):
    """A real window holding two albums, reached the way a load reaches them."""
    made = build(RememberingStore(), RecordingPlayer())
    made.show_library((PLANETS, SIMPLE), ART)
    application.processEvents()
    yield made
    made.close()


def _titles(window) -> list[str]:
    """The album titles the tree is showing, top to bottom."""
    model = window._model
    return [
        model.data(model.index(row, Column.TITLE, QModelIndex()))
        for row in range(model.rowCount(QModelIndex()))
    ]


class TestNarrowing:
    def test_the_whole_library_shows_with_nothing_asked(self, window) -> None:
        assert _titles(window) == ["The Planets", "Simple Things"]

    def test_an_album_title_narrows_to_that_album(self, window) -> None:
        window.search_changed("simple")
        assert _titles(window) == ["Simple Things"]

    def test_an_album_artist_narrows_to_that_album(self, window) -> None:
        window.search_changed("zero 7")
        assert _titles(window) == ["Simple Things"]

    def test_a_track_narrows_to_its_album(self, window) -> None:
        window.search_changed("venus")
        assert _titles(window) == ["The Planets"]

    def test_the_album_is_kept_whole(self, window) -> None:
        """B: every track stays, so the album reads as it always does."""
        window.search_changed("venus")
        model = window._model
        album = model.index(0, Column.TITLE, QModelIndex())
        assert model.rowCount(album) == PLANETS.track_count

    def test_a_phrase_matching_nothing_empties_the_library(self, window) -> None:
        window.search_changed("saturn")
        assert _titles(window) == []

    def test_clearing_brings_everything_back(self, window) -> None:
        window.search_changed("venus")
        window.search_changed("")
        assert _titles(window) == ["The Planets", "Simple Things"]

    def test_the_art_is_narrowed_with_the_albums(self, window) -> None:
        window.search_changed("venus")
        assert set(window._model._art) == {PLANETS.identity.art_key}


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


class TestTheButton:
    def test_it_opens_and_closes_the_box(self, window) -> None:
        window.toggle_search()
        assert window._tray.searching
        window.toggle_search()
        assert not window._tray.searching

    def test_closing_restores_the_library(self, window) -> None:
        window.toggle_search()
        window._tray.search_box.setText("venus")
        assert _titles(window) == ["The Planets"]
        window.toggle_search()
        assert _titles(window) == ["The Planets", "Simple Things"]


NEPTUNE = _track("Neptune", 1, disc=2)
DOUBLE = Album(
    identity=AlbumIdentity(album_artist="Holst", title="Both Suites"),
    tracks=(_track("Venus", 1), NEPTUNE),
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


class TestTheCoverView:
    """The sleeves have no rows to expand, so the pane under them is opened."""

    def test_the_sleeve_opens_on_the_track_that_was_hit(self, window) -> None:
        window.toggle_view()
        assert window.showing_covers
        window.search_changed("venus")
        assert window._shown_album is PLANETS
        showing = window._model.track_at(window._album_pane.current_index())
        assert showing is not None
        assert showing.title == "Venus"


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


class TestThePaneUnderTheSleeves:
    """What is open stays open; only an album that has gone takes it away.

    Replacing every row leaves the pane rooted at an index that no longer
    means that album. Left alone it re-roots on the whole library and lists it
    down both columns, which is the duplication these guard against.
    """

    def _open_planets(self, window):
        """Open The Planets under the sleeves, with Mars chosen in it."""
        window.toggle_view()
        window.open_album_at(window._model.index(0, Column.TITLE, QModelIndex()))
        mars = PLANETS.tracks[1]
        window._album_pane.columns[0].setCurrentIndex(window._model.index_for(mars))
        return mars

    def test_clearing_the_field_leaves_the_album_open_as_it_was(self, window) -> None:
        mars = self._open_planets(window)
        window.search_changed("mars")
        window.search_changed("")
        assert window._shown_album is PLANETS
        assert window._model.track_at(window._album_pane.current_index()) is mars

    def test_the_pane_is_rooted_at_the_album_not_the_library(self, window) -> None:
        """The duplication itself: both columns rooted at the invisible root."""
        self._open_planets(window)
        window.search_changed("mars")
        window.search_changed("")
        for column in window._album_pane.columns:
            assert column.rootIndex().isValid()
            assert window._model.album_at(column.rootIndex()) is PLANETS

    def test_an_album_still_shown_keeps_its_place(self, window) -> None:
        """The Planets still matches, so nothing about the pane changes."""
        mars = self._open_planets(window)
        window.search_changed("planets")
        assert window._shown_album is PLANETS
        assert window._model.track_at(window._album_pane.current_index()) is mars

    def test_an_album_that_has_gone_shuts_the_pane(self, window) -> None:
        """No row anywhere for it, so there is nothing to be rooted at."""
        self._open_planets(window)
        window.search_changed("zero")
        assert window._shown_album is None

    def test_a_hit_still_wins_over_what_was_open(self, window) -> None:
        """Typing a track's name points at that track rather than keeping the
        one that happened to be chosen before."""
        self._open_planets(window)
        window.search_changed("venus")
        showing = window._model.track_at(window._album_pane.current_index())
        assert showing is not None
        assert showing.title == "Venus"
