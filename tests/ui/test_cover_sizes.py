"""Choosing how large a sleeve is drawn in the grid.

Three sizes, stepped through by one button in the bottom strip which names the
size it would move to rather than the one on show, exactly as the view toggle
beside it does. The choice outlasts the session, as the view and the sort order
already did.

Changing the size reads the covers again, because what was read is at the old
size: keeping it would either blur a grown grid or hold more memory than the
chosen size asks for. The second read comes out of Stellody's own store.
"""

from __future__ import annotations

import pytest
from conftest import RecordingPlayer
from PySide6.QtGui import QImage
from PySide6.QtWidgets import QApplication
from tray_support import RememberingStore, build

from stellody.shared import resources
from stellody.ui.covering import (
    COVER_SIZES,
    DEFAULT_COVER_SIZE,
    CoverSize,
    next_cover_size,
)
from stellody.ui.settings_keys import SETTING_COVER_SIZE
from stellody.ui.tiles import tile_size


@pytest.fixture
def window(application: QApplication):
    """A real window holding one album."""
    made = build(RememberingStore(), RecordingPlayer())
    yield made
    made.close()


class TestTheSizesThemselves:
    def test_there_are_three_of_them(self) -> None:
        assert COVER_SIZES == (
            CoverSize.MEDIUM,
            CoverSize.LARGE,
            CoverSize.EXTRA_LARGE,
        )

    def test_each_is_larger_than_the_one_before(self) -> None:
        assert list(COVER_SIZES) == sorted(COVER_SIZES)

    def test_none_of_them_asks_for_more_than_the_store_keeps(self) -> None:
        """Scaling past what was kept invents detail the file never held."""
        from stellody.infrastructure.artwork import THUMBNAIL_PX

        assert max(COVER_SIZES) <= THUMBNAIL_PX

    def test_the_step_wraps_round_at_the_largest(self) -> None:
        assert next_cover_size(CoverSize.MEDIUM) is CoverSize.LARGE
        assert next_cover_size(CoverSize.LARGE) is CoverSize.EXTRA_LARGE
        assert next_cover_size(CoverSize.EXTRA_LARGE) is CoverSize.MEDIUM

    def test_a_tile_grows_with_the_sleeve_it_holds(self) -> None:
        small = tile_size(int(CoverSize.MEDIUM))
        big = tile_size(int(CoverSize.EXTRA_LARGE))
        assert big.width() > small.width()
        assert big.height() > small.height()

    def test_the_names_under_a_sleeve_do_not_grow_with_it(self) -> None:
        """A title is the same title at any size, so it gets the same room."""
        small = tile_size(int(CoverSize.MEDIUM))
        big = tile_size(int(CoverSize.EXTRA_LARGE))
        assert big.height() - big.width() == small.height() - small.width()


class TestSteppingThroughThem:
    def test_a_first_run_starts_at_the_middle_size(self, window) -> None:
        assert window._cover_size is DEFAULT_COVER_SIZE

    def test_the_button_steps_to_the_next_size(self, window) -> None:
        """The control pressed, not the handler called: it is dead over the
        list, so a press there would have proved nothing at all."""
        window.toggle_view()
        window._bottom_tray.showing.size_button.click()
        assert window._cover_size is next_cover_size(DEFAULT_COVER_SIZE)

    def test_the_tiles_and_the_grid_grow_together(self, window) -> None:
        """A view keeps the grid size it was given, so both have to be told."""
        was = window._grid.gridSize()
        window.toggle_cover_size()
        assert window._tiles.cover_px == int(window._cover_size)
        assert window._grid.gridSize().width() > was.width()
        assert window._grid.gridSize().height() > was.height()

    def test_the_button_names_the_size_it_would_move_to(self, window) -> None:
        window.show_cover_size_choice(CoverSize.LARGE)
        assert "extra large" in window._bottom_tray.showing.size_button.toolTip()

    def test_the_choice_is_written_down(self, window) -> None:
        window.show_cover_size_choice(CoverSize.EXTRA_LARGE)
        stored = window._settings.settings[SETTING_COVER_SIZE]
        assert stored == str(int(CoverSize.EXTRA_LARGE))

    def test_the_choice_survives_a_restart(self, application: QApplication) -> None:
        remembered = RememberingStore({SETTING_COVER_SIZE: str(int(CoverSize.LARGE))})
        made = build(remembered, RecordingPlayer())
        assert made._cover_size is CoverSize.LARGE
        made.close()

    def test_a_stored_size_nobody_offers_falls_back(
        self, application: QApplication
    ) -> None:
        """A grid drawn at a number nobody chose is worse than the default."""
        made = build(RememberingStore({SETTING_COVER_SIZE: "77"}), RecordingPlayer())
        assert made._cover_size is DEFAULT_COVER_SIZE
        made.close()

    def test_the_button_is_dead_over_the_list(self, window) -> None:
        """The size means nothing there, so the ring skips it and it shows no border."""
        assert not window.showing_covers
        assert not window._bottom_tray.showing.size_button.isEnabled()
        window.toggle_view()
        assert window._bottom_tray.showing.size_button.isEnabled()

    def test_the_button_is_in_the_ring(self, window) -> None:
        assert (
            window._bottom_tray.showing.size_button in window._bottom_tray.ring_stops()
        )


class TestReadingAgainAtTheNewSize:
    def test_the_covers_are_dropped_so_they_are_read_again(self, window) -> None:
        album = window._model._albums[0]
        window._model.set_cover(album.identity.art_key, None)
        window.toggle_cover_size()
        assert window._model.cover_px == int(window._cover_size)
        assert album.identity.art_key not in window._model._covers

    def test_asking_for_the_same_size_reads_nothing_again(self, window) -> None:
        album = window._model._albums[0]
        window._model.set_cover(album.identity.art_key, None)
        window.show_cover_size_choice(window._cover_size)
        assert album.identity.art_key in window._model._covers


class TestTheArtwork:
    """One picture per size; three different pictures.

    Worth asserting because the three arrived in the wrong repository once and
    the only symptom was a button drawing nothing at all.
    """

    def test_each_size_has_a_picture_that_loads(
        self, application: QApplication
    ) -> None:
        for resolver in (
            resources.medium_grid_icon_path,
            resources.large_grid_icon_path,
            resources.extra_large_grid_icon_path,
        ):
            path = resolver()
            assert path is not None, resolver.__name__
            assert not QImage(str(path)).isNull(), resolver.__name__

    def test_the_three_are_different_pictures(self, application: QApplication) -> None:
        """A button that draws the same thing at every size says nothing."""
        drawn = set()
        for resolver in (
            resources.medium_grid_icon_path,
            resources.large_grid_icon_path,
            resources.extra_large_grid_icon_path,
        ):
            # Named rather than read off a chain of temporaries: bits() on one
            # hands back a buffer whose owner is already gone, which segfaults.
            image = QImage(str(resolver()))
            drawn.add(image.constBits().tobytes())
        assert len(drawn) == 3
