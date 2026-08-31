"""The album opened under the sleeves and what keeps it open.

Replacing every row leaves the pane rooted at an index that no longer means
that album. Left alone it re-roots on the whole library and lists it down both
columns, which is the duplication these guard against. Three things replace
every row: a search keystroke, inverting the order and a rescan.
"""

from __future__ import annotations

import pytest
from library_support import ART, PLANETS, SIMPLE, library_window
from PySide6.QtCore import QBuffer, QIODevice, QModelIndex
from PySide6.QtGui import QColor, QImage
from PySide6.QtWidgets import QApplication

from stellody.domain.album import Album
from stellody.ui.row_text import Column


@pytest.fixture
def window(application: QApplication):
    yield from library_window(application)


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


class TestOtherThingsThatReplaceEveryRow:
    """A search is not the only one. Inverting the order and rescanning both
    replace every row, so both left the pane rooted at rows that had gone."""

    def _open_planets(self, window):
        window.toggle_view()
        window.open_album_at(window._model.index(0, Column.TITLE, QModelIndex()))
        mars = PLANETS.tracks[1]
        window._album_pane.columns[0].setCurrentIndex(window._model.index_for(mars))
        return mars

    def test_inverting_the_order_keeps_the_album_and_the_track(self, window) -> None:
        mars = self._open_planets(window)
        window.toggle_order()
        assert window._shown_album is PLANETS
        assert window._model.album_at(window._album_pane.columns[0].rootIndex()) is (
            PLANETS
        )
        assert window._model.track_at(window._album_pane.current_index()) is mars

    def test_a_rescan_keeps_the_album_though_it_is_built_afresh(self, window) -> None:
        """The albums come back as different objects, so sameness is identity."""
        self._open_planets(window)
        again = Album(identity=PLANETS.identity, tracks=PLANETS.tracks)
        assert again is not PLANETS
        window.show_library((again, SIMPLE), ART)
        assert window._shown_album is again
        assert window._album_pane.columns[0].rootIndex().isValid()

    def test_an_album_a_rescan_dropped_shuts_the_pane(self, window) -> None:
        self._open_planets(window)
        window.show_library((SIMPLE,), ART[1:])
        assert window._shown_album is None


def _png(colour: str, size: int = 64) -> bytes:
    """Real image bytes to stand in for a cover that has just been read."""
    image = QImage(size, size, QImage.Format.Format_RGB32)
    image.fill(QColor(colour).rgb())
    buffer = QBuffer()
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    image.save(buffer, "PNG")
    data = bytes(buffer.data())
    buffer.close()
    return data


def _pane_colour(window) -> str:
    """The colour of the sleeve the pane is drawing."""
    return window._album_pane.cover.pixmap().toImage().pixelColor(0, 0).name()


class TestTheSleeveOnTheOpenAlbum:
    """The pane takes its sleeve as it opens, which is usually before there is
    one: a cover is read on a thread of its own. Taking it only then left the
    placeholder there until the album was opened again; the placeholder is
    painted in the pane's own colour, so it read as no sleeve rather than as
    one still on its way.
    """

    def _open(self, window) -> None:
        window.toggle_view()
        window.open_album_at(window._model.index(0, Column.TITLE, QModelIndex()))

    def test_a_cover_read_after_it_opened_reaches_the_pane(self, window) -> None:
        self._open(window)
        assert _pane_colour(window) != QColor("red").name()
        window._on_cover(PLANETS.identity.art_key, _png("red"))
        assert _pane_colour(window) == QColor("red").name()

    def test_a_cover_for_another_album_leaves_it_alone(self, window) -> None:
        self._open(window)
        window._on_cover(SIMPLE.identity.art_key, _png("red"))
        assert _pane_colour(window) != QColor("red").name()

    def test_a_cover_arriving_with_nothing_open_is_harmless(self, window) -> None:
        window.toggle_view()
        window._on_cover(PLANETS.identity.art_key, _png("red"))
        assert window._shown_album is None

    def test_a_search_opens_the_pane_on_a_sleeve_already_read(self, window) -> None:
        """The whole of it, end to end: what a keystroke opens has its sleeve.

        The keystroke used to throw every read cover away, so the pane opened
        on the placeholder and never took the real one.
        """
        window.toggle_view()
        window._on_cover(PLANETS.identity.art_key, _png("red"))
        window.search_changed("venus")
        assert window._shown_album is PLANETS
        assert _pane_colour(window) == QColor("red").name()
