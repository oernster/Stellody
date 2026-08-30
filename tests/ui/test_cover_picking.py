"""Picking a picture in the chooser, then keeping the one that was picked.

Split from the tests for what the chooser SHOWS, along the seam between the two
halves of the dialog: over there is what a search puts on screen, here is what a
listener does to it. The archive is stood in for in both.
"""

from __future__ import annotations

import time

import pytest
from cover_support import BACK, FRONT, KEPT, FakeArtwork, FakeSearch
from PySide6.QtCore import QBuffer, QIODevice, QThread
from PySide6.QtGui import QColor, QIcon, QImage
from PySide6.QtWidgets import QApplication
from tray_support import album

from stellody.application.choosing_covers import ChooseCover
from stellody.ui.cover_chooser import GRID_NAME, UNREACHABLE, CoverChooser
from stellody.ui.theme import FOCUS_WIDTH_PX, Mode, palette_for, stylesheet

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


class TestSayingWhichPictureIsPicked:
    """A tint alone did not read against a wall of sleeves.

    The ring is stated in the palette rather than painted in the dialog, so
    there is one home for the colour and it is the same green the rest of the
    application rings a chosen thing with.
    """

    def test_the_grid_is_named_so_the_theme_can_reach_its_tiles(
        self, application
    ) -> None:
        dialog = _opened(FakeSearch(), application)
        assert dialog.grid.objectName() == GRID_NAME
        dialog.reject()

    @pytest.mark.parametrize("mode", tuple(Mode))
    def test_a_picked_tile_wears_the_ring_colour(self, mode: Mode) -> None:
        rule = _selected_rule(stylesheet(mode))
        assert palette_for(mode).ring in rule
        assert f"{FOCUS_WIDTH_PX}px solid" in rule

    @pytest.mark.parametrize("mode", tuple(Mode))
    def test_an_unpicked_tile_wears_the_same_border_in_nothing(
        self, mode: Mode
    ) -> None:
        """Transparent rather than absent, so picking one never reflows the grid."""
        sheet = stylesheet(mode)
        plain = sheet[sheet.index(f"QListWidget#{GRID_NAME}::item {{") :]
        assert "solid transparent" in plain.split("}")[0]

    @pytest.mark.parametrize("mode", tuple(Mode))
    def test_the_ring_is_only_on_the_chooser_grid(self, mode: Mode) -> None:
        """The library's own views choose nothing, so they are left alone."""
        for line in stylesheet(mode).splitlines():
            if palette_for(mode).ring in line:
                continue
            assert "QListWidget::item:selected" not in line

    def test_picking_a_picture_does_not_wash_its_colour_out(self, application) -> None:
        """Qt draws a selected icon in its own Selected mode, which dimmed it.

        The one tile a listener is comparing against the others was the one
        they could no longer see properly. Measured before the fix: the picked
        tile rendered grey where its picture was brown.
        """
        pictures = {FRONT.thumbnail_url: _png_bytes()}
        dialog = _opened(FakeSearch(pictures=pictures), application)
        dialog.grid.setCurrentRow(0)
        icon = dialog.grid.item(0).icon()
        size = icon.availableSizes()[0]
        assert (
            icon.pixmap(size, QIcon.Mode.Selected).toImage()
            == icon.pixmap(size, QIcon.Mode.Normal).toImage()
        )
        dialog.reject()


def _selected_rule(sheet: str) -> str:
    """The block styling a picked tile."""
    start = sheet.index(f"QListWidget#{GRID_NAME}::item:selected")
    return sheet[start : sheet.index("}", start)]


class TestPickingAPicture:
    def test_nothing_can_be_kept_until_something_is_picked(self, application) -> None:
        dialog = _opened(FakeSearch(), application)
        assert not dialog.keep_button.isEnabled()
        assert dialog.picked() is None
        dialog.reject()

    def test_picking_a_tile_offers_to_keep_it(self, application) -> None:
        dialog = _opened(FakeSearch(), application)
        dialog.grid.setCurrentRow(1)
        assert dialog.keep_button.isEnabled()
        assert dialog.picked() == BACK
        dialog.reject()

    def test_keeping_hands_back_the_picture_and_closes(self, application) -> None:
        artwork = FakeArtwork()
        search = FakeSearch(pictures={FRONT.image_url: _png_bytes()})
        dialog = _opened(search, application, artwork)
        handed: list[tuple[str, object]] = []
        dialog.chosen.connect(lambda key, data: handed.append((key, data)))
        dialog.grid.setCurrentRow(0)
        dialog.keep_picked()
        _settle(dialog, application)
        assert handed == [(ART_KEY, KEPT)]
        assert artwork.kept == {ART_KEY: KEPT}
        assert not dialog.isVisible()

    def test_a_picture_that_cannot_be_fetched_leaves_the_chooser_open(
        self, application
    ) -> None:
        dialog = _opened(FakeSearch(), application)
        handed: list[tuple[str, object]] = []
        dialog.chosen.connect(lambda key, data: handed.append((key, data)))
        dialog.grid.setCurrentRow(0)
        dialog.keep_picked()
        _settle(dialog, application)
        assert handed == []
        assert dialog.status.text() == UNREACHABLE
        assert dialog.keep_button.isEnabled()
        dialog.reject()

    def test_keeping_with_nothing_picked_asks_for_nothing(self, application) -> None:
        search = FakeSearch()
        dialog = _opened(search, application)
        fetched = list(search.fetched)
        dialog.keep_picked()
        assert search.fetched == fetched
        dialog.reject()


class TestClosingTheChooser:
    def test_closing_lets_go_of_the_search(self, application) -> None:
        dialog = _opened(FakeSearch(), application)
        dialog.reject()
        assert not dialog.searching
        assert not dialog.isVisible()
