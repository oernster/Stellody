"""Switching between the list and the sleeves, then opening one album.

Both views are the same model, so what is asserted here is that the switch
changes only which one is on show. Picking a sleeve opens the album under the
grid rather than replacing it, so the sleeves stay where they were.
"""

from __future__ import annotations

import pytest
from conftest import RecordingPlayer
from PySide6.QtCore import QModelIndex
from PySide6.QtWidgets import QApplication
from tray_support import RememberingStore, build

from stellody.ui.row_text import Column
from stellody.ui.settings_keys import FALSE, SETTING_COVERS, TRUE


@pytest.fixture
def window(application: QApplication):
    """A real window holding one album."""
    made = build(RememberingStore(), RecordingPlayer())
    yield made
    made.close()


def _first_album(window) -> QModelIndex:
    """Where the one album sits in the model."""
    return window._model.index(0, Column.TITLE, QModelIndex())


class TestSwitchingViews:
    def test_the_list_is_what_a_first_run_shows(self, window) -> None:
        assert not window.showing_covers

    def test_the_toggle_swaps_the_view(self, window) -> None:
        window.toggle_view()
        assert window.showing_covers
        window.toggle_view()
        assert not window.showing_covers

    def test_the_choice_is_written_down(self, window) -> None:
        window.toggle_view()
        assert window._settings.settings[SETTING_COVERS] == TRUE
        window.toggle_view()
        assert window._settings.settings[SETTING_COVERS] == FALSE

    def test_the_choice_survives_a_restart(self, application: QApplication) -> None:
        """It outlasts a session exactly as the sort order and appearance do."""
        remembered = RememberingStore({SETTING_COVERS: TRUE})
        made = build(remembered, RecordingPlayer())
        assert made.showing_covers
        made.close()

    def test_both_views_show_the_same_model(self, window) -> None:
        """Neither can disagree about what the library holds."""
        assert window._grid.model() is window._model
        assert window._tree.model() is window._model

    def test_the_order_is_kept_across_a_switch(self, window) -> None:
        """There is one order because there is one model."""
        window.toggle_order()
        was = window._model.descending
        window.toggle_view()
        assert window._model.descending is was
        assert window._grid.model().descending is was


class TestOpeningAnAlbum:
    def test_the_pane_starts_closed(self, window) -> None:
        assert not window._album_pane.isVisible()

    def test_picking_a_sleeve_opens_that_album(self, window) -> None:
        window.toggle_view()
        window._grid.setCurrentIndex(_first_album(window))
        pane = window._album_pane
        assert pane.title.text() == "The Planets"
        assert pane.artist.text() == "Holst"

    def test_the_pane_lists_the_album_it_opened_on(self, window) -> None:
        """The same model rooted at the album, not a second copy of it."""
        window.toggle_view()
        where = _first_album(window)
        window._grid.setCurrentIndex(where)
        pane = window._album_pane
        for column in pane.columns:
            assert column.model() is window._model
            assert column.rootIndex() == where

    def test_closing_the_pane_leaves_the_grid_alone(self, window) -> None:
        window.toggle_view()
        window._grid.setCurrentIndex(_first_album(window))
        window.close_album()
        for column in window._album_pane.columns:
            assert column.rootIndex() == QModelIndex()
        assert window.showing_covers, "the sleeves stay where they were"

    def test_going_back_to_the_list_shuts_the_pane(self, window) -> None:
        window.toggle_view()
        window._grid.setCurrentIndex(_first_album(window))
        window.toggle_view()
        for column in window._album_pane.columns:
            assert column.rootIndex() == QModelIndex()

    def test_playing_the_open_album_starts_its_first_track(self, window) -> None:
        window.toggle_view()
        window._grid.setCurrentIndex(_first_album(window))
        window.play_shown_album()
        assert window._transport.current is not None

    def test_playing_with_nothing_open_does_nothing(self, window) -> None:
        """The button is only reachable while the pane is open; this is the guard."""
        window.play_shown_album()
        assert window._transport.current is None


class TestTheButtonItself:
    def test_pressing_the_button_switches_the_view(self, window) -> None:
        """The handler was reachable while the button was not connected to it.

        Every earlier test here called the method, so all of them passed while
        pressing the control did nothing at all. This one presses the control.
        """
        assert not window.showing_covers
        window._bottom_tray.showing.view_button.click()
        assert window.showing_covers, "the button is wired to the handler"
        window._bottom_tray.showing.view_button.click()
        assert not window.showing_covers

    def test_pressing_the_button_moves_the_view_that_is_shown(self, window) -> None:
        """Not merely the flag: the holder has to change what it is showing."""
        listed = window._library.currentWidget()
        window._bottom_tray.showing.view_button.click()
        assert window._library.currentWidget() is not listed


class TestWhatEachViewCanBeAskedFor:
    """Expanding and collapsing belong to the list, which is the nested one."""

    def test_the_list_offers_expanding_and_collapsing(self, window) -> None:
        window.show_covers(False)
        assert window._expand_action.isEnabled()
        assert window._collapse_action.isEnabled()

    def test_the_sleeves_do_not(self, window) -> None:
        """A flat grid of albums has nothing inside an album to open.

        They stayed live in that view and did nothing when pressed, which is
        the one thing this application's own rule forbids: a control that
        cannot act says so rather than staying quiet about it.
        """
        window.show_covers(True)
        assert not window._expand_action.isEnabled()
        assert not window._collapse_action.isEnabled()

    def test_switching_back_offers_them_again(self, window) -> None:
        """Disabled for the view, not for the session."""
        window.show_covers(True)
        window.show_covers(False)
        assert window._expand_action.isEnabled()
        assert window._collapse_action.isEnabled()

    def test_a_window_opening_on_the_sleeves_starts_without_them(
        self, application: QApplication
    ) -> None:
        """The restored view has to say so too, not only a switch made by hand."""
        opened = build(RememberingStore({SETTING_COVERS: TRUE}), RecordingPlayer())
        opened.show()
        assert opened.showing_covers
        assert not opened._expand_action.isEnabled()
        opened.close()
