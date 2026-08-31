"""The chooser a listener sees, plus the one entry that opens it.

The dialog is real and so is the thread under it. What is stood in for is the
archive, which would otherwise open a connection: no test here reaches the
network, which the structural guard states for the whole package anyway.

The menu tests are the other half of the same promise. A window built without
the service offers nothing to press, so the outward reach is not merely
unlikely from a test, it is absent.
"""

from __future__ import annotations

import threading
import time

from conftest import RecordingPlayer
from cover_support import BACK, FRONT, FakeArtwork, FakeSearch
from PySide6.QtCore import QBuffer, QIODevice, QModelIndex, QThread
from PySide6.QtGui import QColor, QImage
from PySide6.QtWidgets import QApplication
from tray_support import RememberingStore, album, build

from stellody.application.choosing_covers import ChooseCover
from stellody.ui.cover_chooser import (
    CANCEL,
    CLOSE,
    NOTHING,
    REFUSED,
    CoverChooser,
)
from stellody.ui.row_text import Column
from stellody.ui.theme import Mode

SETTLE_SECONDS = 8.0
POLL_MS = 2
ART_KEY = album().identity.art_key


def _settle(dialog: CoverChooser, application: QApplication) -> None:
    """Let the search finish and every answer reach the dialog."""
    deadline = time.monotonic() + SETTLE_SECONDS
    while time.monotonic() < deadline:
        application.processEvents()
        if not dialog.searching:
            application.processEvents()
            return
        QThread.msleep(POLL_MS)


def _chooser(search, artwork=None) -> ChooseCover:
    """The real service over an archive that answers from a script."""
    return ChooseCover(search, artwork or FakeArtwork())


def _opened(search, application, artwork=None) -> CoverChooser:
    """A chooser dialog whose search has been let finish."""
    dialog = CoverChooser(_chooser(search, artwork), album(), Mode.DARK)
    _settle(dialog, application)
    return dialog


def _labels(dialog: CoverChooser) -> list[str]:
    """What is written under each tile."""
    return [dialog.grid.item(row).text() for row in range(dialog.grid.count())]


class TestWhatTheChooserShows:
    def test_a_tile_is_drawn_for_every_picture_on_offer(self, application) -> None:
        dialog = _opened(FakeSearch(), application)
        assert dialog.grid.count() == 2
        dialog.reject()

    def test_a_tile_names_its_release_and_the_largest_size_offered(
        self, application
    ) -> None:
        dialog = _opened(FakeSearch(), application)
        assert _labels(dialog) == [FRONT.described, BACK.described]
        assert "1200 px" in _labels(dialog)[0]
        dialog.reject()

    def test_a_picture_that_arrives_is_drawn_on_its_own_tile(self, application) -> None:
        pictures = {FRONT.thumbnail_url: _png_bytes()}
        dialog = _opened(FakeSearch(pictures=pictures), application)
        assert not dialog.grid.item(0).icon().isNull()
        dialog.reject()

    def test_it_says_what_came_back_once_the_search_has_finished(
        self, application
    ) -> None:
        dialog = _opened(FakeSearch(), application)
        assert dialog.status.text() == "2 pictures on offer. Pick one to keep it."
        dialog.reject()

    def test_an_album_nothing_was_found_for_is_told_so(self, application) -> None:
        dialog = _opened(FakeSearch(candidates=()), application)
        assert dialog.status.text() == NOTHING
        assert dialog.grid.count() == 0
        dialog.reject()

    def test_a_refused_search_is_never_reported_as_nothing_found(
        self, application
    ) -> None:
        """The archive made no claim about this album, so neither does this.

        Measured 2026-08-31, MusicBrainz refused 6 of 10 asks at the rate its
        own terms ask for. Saying "nothing came back for this album" there
        tells a listener their album has no art anywhere, which is both untrue
        and the exact thing they will disbelieve.
        """
        dialog = _opened(FakeSearch(candidates=(), refused=True), application)
        assert dialog.status.text() == REFUSED
        assert dialog.status.text() != NOTHING
        assert dialog.grid.count() == 0
        dialog.reject()

    def test_one_picture_is_counted_as_one(self, application) -> None:
        dialog = _opened(FakeSearch(candidates=(FRONT,)), application)
        assert dialog.status.text() == "One picture on offer. Pick it to keep it."
        dialog.reject()


class TestDrawingTheWait:
    """A search takes 10 to 15 seconds against the real archive.

    A dialog that says it is working while showing nothing that moves is one
    somebody decides has hung, so the wait is drawn. `isVisibleTo` is asked
    rather than `isVisible`, since intent is the question here and a dialog
    nobody showed answers False to everything.
    """

    def test_it_opens_already_showing_that_it_is_working(self, application) -> None:
        gate = threading.Event()
        dialog = CoverChooser(_chooser(FakeSearch(gate=gate)), album(), Mode.DARK)
        try:
            assert dialog.progress.isVisibleTo(dialog)
            assert dialog.progress.maximum() == 0, "nothing to count yet"
            assert dialog.close_button.text() == CANCEL
        finally:
            gate.set()
            _settle(dialog, application)
            dialog.reject()

    def test_the_wait_stops_being_drawn_once_the_search_is_done(
        self, application
    ) -> None:
        dialog = _opened(FakeSearch(), application)
        assert not dialog.progress.isVisibleTo(dialog)
        assert dialog.close_button.text() == CLOSE
        dialog.reject()

    def test_it_counts_the_pictures_once_it_knows_how_many(self, application) -> None:
        pictures = {FRONT.thumbnail_url: _png_bytes(), BACK.thumbnail_url: _png_bytes()}
        dialog = _opened(FakeSearch(pictures=pictures), application)
        assert dialog.progress.maximum() == 2
        assert dialog.progress.value() == 2
        dialog.reject()

    def test_a_refused_search_stops_drawing_a_wait_as_well(self, application) -> None:
        dialog = _opened(FakeSearch(candidates=(), refused=True), application)
        assert not dialog.progress.isVisibleTo(dialog)
        assert dialog.close_button.text() == CLOSE
        dialog.reject()

    def test_keeping_a_picture_draws_a_wait_of_its_own(self, application) -> None:
        dialog = _opened(FakeSearch(), application)
        dialog.grid.setCurrentRow(0)
        dialog.keep_picked()
        assert dialog.progress.isVisibleTo(dialog)
        assert dialog.close_button.text() == CANCEL
        _settle(dialog, application)
        assert not dialog.progress.isVisibleTo(dialog)
        dialog.reject()

    def test_the_wait_can_still_be_cancelled(self, application) -> None:
        gate = threading.Event()
        dialog = CoverChooser(_chooser(FakeSearch(gate=gate)), album(), Mode.DARK)
        dialog.reject()
        assert not dialog.searching
        gate.set()
        _settle(dialog, application)


class TestTheEntryThatOpensIt:
    def test_a_window_without_the_service_offers_no_lookup(self, application) -> None:
        window = build(RememberingStore(), RecordingPlayer())
        try:
            assert not window.can_choose_covers
            assert "Find cover art online..." not in _menu_over_album(window)
        finally:
            window.close()

    def test_a_window_with_it_offers_the_lookup_over_an_album(
        self, application
    ) -> None:
        window = build(
            RememberingStore(),
            RecordingPlayer(),
            chooser=_chooser(FakeSearch()),
        )
        try:
            assert window.can_choose_covers
            assert "Find cover art online..." in _menu_over_album(window)
        finally:
            window.close()

    def test_it_is_offered_from_a_row_inside_the_album_too(self, application) -> None:
        """A cover belongs to the album, so any row under it may ask for one.

        The model resolves an album from an index at whatever level it sits,
        which is deliberate. Hiding the entry on a track would mean overriding
        that on the one menu that uses it, to no end a listener would thank us
        for: the album they are pointing into is unambiguous.
        """
        window = build(
            RememberingStore(),
            RecordingPlayer(),
            chooser=_chooser(FakeSearch()),
        )
        try:
            window._tree.expandAll()
            inside = window._model.index(0, Column.TITLE, _album_index(window))
            window.show_transport_menu(
                window._tree.visualRect(inside).center(), window._tree
            )
            labels = {action.text() for action in window._menu.actions()}
            assert window._model.album_at(inside) is not None
            assert "Find cover art online..." in labels
        finally:
            window.close()

    def test_it_is_not_offered_over_empty_space(self, application) -> None:
        window = build(
            RememberingStore(),
            RecordingPlayer(),
            chooser=_chooser(FakeSearch()),
        )
        try:
            window.show_transport_menu(
                window._tree.viewport().rect().bottomRight(), window._tree
            )
            labels = {action.text() for action in window._menu.actions()}
            assert "Find cover art online..." not in labels
        finally:
            window.close()

    def test_choosing_without_the_service_does_nothing(self, application) -> None:
        window = build(RememberingStore(), RecordingPlayer())
        try:
            window.choose_cover(album())
            assert window._cover_dialog is None
        finally:
            window.close()


def _album_index(window) -> QModelIndex:
    """Where the one album sits in the model."""
    return window._model.index(0, Column.TITLE, QModelIndex())


def _menu_over_album(window) -> set[str]:
    """Every label on the menu raised over the album row."""
    index = _album_index(window)
    window.show_transport_menu(window._tree.visualRect(index).center(), window._tree)
    return {action.text() for action in window._menu.actions() if action.text()}


def _png_bytes() -> bytes:
    """A real, tiny image, so what is drawn is drawn rather than mocked."""
    image = QImage(4, 4, QImage.Format.Format_RGB32)
    image.fill(QColor("red"))
    buffer = QBuffer()
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    image.save(buffer, "PNG")
    made = bytes(buffer.data())
    buffer.close()
    return made
