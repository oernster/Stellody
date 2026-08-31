"""Driving the transport from the sleeves rather than from the list.

Three things are asserted here. Right clicking a sleeve offers the same menu
the list carries; Play on it means that album from its first track. Picking
a sleeve leaves a track highlighted, so the play button at the top has
something to start. And the button reads the view that is ON SHOW, since the
list is not what somebody looking at the sleeves is pointing at.
"""

from __future__ import annotations

import pytest
from conftest import RecordingPlayer
from PySide6.QtCore import QModelIndex
from PySide6.QtWidgets import QApplication
from tray_support import RememberingStore, build

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


def _sleeves(window):
    """The grid, shown, with nothing picked in it yet."""
    window.toggle_view()
    return window._grid


def _menu_over(window, view, index) -> dict:
    """The menu that view would show over that row, by label."""
    window.show_transport_menu(view.visualRect(index).center(), view)
    return {action.text(): action for action in window._menu.actions() if action.text()}


class TestTheMenuOverASleeve:
    def test_a_sleeve_offers_the_whole_transport(self, window) -> None:
        grid = _sleeves(window)
        items = _menu_over(window, grid, _first_album(window))
        assert set(items) == {
            "Play",
            "Pause",
            "Stop",
            "Previous track",
            "Next track",
        }

    def test_play_over_a_sleeve_is_offered_with_nothing_loaded(self, window) -> None:
        """On the list this would be dead: an album row carries no track."""
        grid = _sleeves(window)
        assert _menu_over(window, grid, _first_album(window))["Play"].isEnabled()

    def test_play_over_a_sleeve_starts_that_album(self, window) -> None:
        grid = _sleeves(window)
        _menu_over(window, grid, _first_album(window))["Play"].trigger()
        assert (
            window._transport.current
            is window._model.album_at(_first_album(window)).ordered_tracks()[0]
        )

    def test_play_over_the_album_already_loaded_carries_on(self, window) -> None:
        """Starting it again is what next and previous are for."""
        grid = _sleeves(window)
        _menu_over(window, grid, _first_album(window))["Play"].trigger()
        window.toggle_playback()
        was = window._transport.current
        _menu_over(window, grid, _first_album(window))["Play"].trigger()
        assert window._transport.current is was

    def test_the_open_album_carries_the_menu_too(self, window) -> None:
        grid = _sleeves(window)
        grid.setCurrentIndex(_first_album(window))
        column = window._album_pane.columns[0]
        items = _menu_over(window, column, window._album_pane.current_index())
        assert "Play" in items


class TestThePickedAlbumsFirstTrack:
    def test_picking_a_sleeve_highlights_the_first_track(self, window) -> None:
        grid = _sleeves(window)
        grid.setCurrentIndex(_first_album(window))
        highlighted = window._album_pane.current_index()
        assert window._model.track_at(highlighted) is not None
        assert window._model.track_at(highlighted).track_number == 1

    def test_the_play_button_starts_that_track(self, window) -> None:
        """The point of the highlight: a press at the top has a target."""
        grid = _sleeves(window)
        grid.setCurrentIndex(_first_album(window))
        window.toggle_playback()
        assert window._transport.current is not None
        assert window._transport.current.track_number == 1

    def test_the_button_reads_the_view_on_show(self, window) -> None:
        grid = _sleeves(window)
        grid.setCurrentIndex(_first_album(window))
        assert window.highlighted() == window._album_pane.current_index()
        window.toggle_view()
        assert window.highlighted() == window._tree.currentIndex()

    def test_a_second_album_is_what_the_button_then_starts(self, window) -> None:
        """The defect: a loaded track made the button a resume for ever after.

        Picking a second album and pressing play started the first one again,
        because anything loaded turned the press into a resume whatever had
        been chosen since. Only one album is in this library, so the second
        pick is a second TRACK of it, which is the same wrong turn.
        """
        grid = _sleeves(window)
        grid.setCurrentIndex(_first_album(window))
        window.toggle_playback()
        window.toggle_playback()
        assert not window._transport.playing, "paused, so the next press starts"
        pane = window._album_pane
        album = window._model.album_at(_first_album(window))
        second = window._model.index_for(album.ordered_tracks()[1])
        pane.columns[1].setCurrentIndex(second)
        window.toggle_playback()
        assert window._transport.current.track_number == 2

    def test_a_press_while_playing_still_pauses(self, window) -> None:
        """A button showing pause pauses, even with something else picked."""
        grid = _sleeves(window)
        grid.setCurrentIndex(_first_album(window))
        window.toggle_playback()
        assert window._transport.playing
        album = window._model.album_at(_first_album(window))
        second = window._model.index_for(album.ordered_tracks()[1])
        window._album_pane.columns[1].setCurrentIndex(second)
        window.toggle_playback()
        assert not window._transport.playing
        assert window._transport.current.track_number == 1, "it did not jump"

    def test_shutting_the_pane_takes_the_highlight_with_it(self, window) -> None:
        grid = _sleeves(window)
        grid.setCurrentIndex(_first_album(window))
        window.close_album()
        assert not window._album_pane.current_index().isValid()
