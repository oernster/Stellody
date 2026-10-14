"""The name along the foot takes you to the album playing.

Asked for by Oliver on 2026-10-14: with the pane rolled up nothing on screen
says which sleeve the music came from, so finding it meant hunting for the
right cover. Clicking the name, else Go to playing album on the View menu,
goes there and opens it on the track in hand. A search or the genre filter
hiding it is said rather than undone (his ruling the same day).
"""

from __future__ import annotations

from playback_support import album_index, player, track, track_index, window
from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QKeySequence
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from recording_player import RecordingPlayer
from tray_support import RememberingStore, build

from stellody.domain.album import Album
from stellody.domain.identity import AlbumIdentity
from stellody.ui.gliding import GLIDE_MS
from stellody.ui.main_window import MainWindow
from stellody.ui.now_playing import GO_TO_PLAYING_SHORTCUT, PLAYING_HIDDEN

__all__ = ["player", "window"]

FIRST = 0
THIRD = 2
NOTHING_MATCHES = "no album is called this"
# Any size a press can land in; the label's own would be nothing while empty.
LINE_ROOM = QSize(200, 20)
# Enough albums that the grid scrolls, with one played well down it; measured
# at this window size, the next size up carries that sleeve off the bottom.
SHELF_SIZE = 40
DEEP_ROW = 30
WINDOW_ROOM = QSize(1000, 800)


def shelf() -> tuple[Album, ...]:
    """A library long enough to scroll, each album its own."""
    return tuple(
        Album(
            identity=AlbumIdentity(album_artist=f"Artist {n}", title=f"Album {n}"),
            tracks=(track(1),),
        )
        for n in range(SHELF_SIZE)
    )


def playing_third_under_a_rolled_up_pane(made: MainWindow) -> None:
    """The reported case: the sleeve still current, its pane rolled up."""
    made.show_covers(True)
    made._grid.setCurrentIndex(album_index(made))
    made.activate(track_index(made, THIRD))
    made._poll_transport()
    made.close_album()


class TestUnderTheSleeves:
    def test_it_reopens_the_pane_on_the_track_in_hand(
        self, window: MainWindow, player: RecordingPlayer
    ) -> None:
        playing_third_under_a_rolled_up_pane(window)
        assert not window._album_pane.isVisibleTo(window), "premise: rolled up"
        window.show_playing_album()
        assert window._album_pane.isVisibleTo(window)
        assert window.shown_index == album_index(window)
        assert window._album_pane.current_index().row() == THIRD

    def test_a_click_on_the_name_does_the_same(
        self, window: MainWindow, player: RecordingPlayer
    ) -> None:
        """A real press on the label, not the handler called."""
        playing_third_under_a_rolled_up_pane(window)
        line = window._now_playing
        line.adjustSize()
        QTest.mouseClick(line, Qt.MouseButton.LeftButton)
        assert window._album_pane.isVisibleTo(window)


class TestAfterTheSleevesChangeSize:
    """Reported by Oliver on 2026-10-14 and reproduced offscreen the same day.

    With the pane still open, a step to the next size carried the playing
    sleeve below the viewport; going to it then found its album already open
    and moved nothing, so it only worked at the size it was opened at.
    """

    def test_the_grid_travels_back_to_the_playing_sleeve(
        self, application: QApplication
    ) -> None:
        made = build(RememberingStore(), RecordingPlayer(), leave=lambda: None)
        made._model.set_albums(shelf())
        made.resize(WINDOW_ROOM)
        made.show()
        made.show_covers(True)
        sleeve = made._model.index(DEEP_ROW, 0)
        made._grid.setCurrentIndex(sleeve)
        made.activate(made._model.index(FIRST, 0, sleeve))
        made._poll_transport()
        made.toggle_cover_size()
        application.processEvents()
        grid = made._grid
        port = grid.viewport().rect()
        assert not port.contains(grid.visualRect(sleeve)), "premise: moved off"
        made.go_to_playing_action.trigger()
        grid.glide.setCurrentTime(GLIDE_MS)
        assert port.contains(grid.visualRect(sleeve))
        made.close()


class TestInTheList:
    def test_it_moves_the_highlight_back_to_the_track_in_hand(
        self, window: MainWindow, player: RecordingPlayer
    ) -> None:
        window.activate(track_index(window, THIRD))
        window._poll_transport()
        window._tree.setCurrentIndex(track_index(window, FIRST))
        window.show_playing_album()
        assert window._tree.currentIndex() == track_index(window, THIRD)


class TestTheMenuEntry:
    def test_it_is_on_the_view_menu_under_its_shortcut(
        self, window: MainWindow
    ) -> None:
        action = window.go_to_playing_action
        view = next(
            entry.menu()
            for entry in window.menuBar().actions()
            if entry.text() == "&View"
        )
        assert action in view.actions()
        assert action.shortcut() == QKeySequence(GO_TO_PLAYING_SHORTCUT)

    def test_it_is_offered_only_while_a_track_is_in_hand(
        self, window: MainWindow, player: RecordingPlayer
    ) -> None:
        """Paused still counts; a stop gives the track back."""
        action = window.go_to_playing_action
        assert not action.isEnabled(), "nothing in hand yet"
        window.activate(track_index(window, THIRD))
        window._poll_transport()
        assert action.isEnabled()
        window.toggle_playback()
        assert action.isEnabled(), "paused is still in hand"
        window.stop_playback()
        assert not action.isEnabled()


class TestNothingToGoTo:
    def test_an_empty_name_takes_nobody_anywhere(self, window: MainWindow) -> None:
        window.show_covers(True)
        line = window._now_playing
        # Given room of its own, so the press lands on the label rather than
        # on nothing: having nothing in hand is what has to refuse it.
        line.resize(LINE_ROOM)
        QTest.mouseClick(line, Qt.MouseButton.LeftButton)
        assert not window._album_pane.isVisibleTo(window)

    def test_an_album_hidden_by_a_search_is_said_and_left_hidden(
        self, window: MainWindow, player: RecordingPlayer
    ) -> None:
        window.activate(track_index(window, THIRD))
        window._poll_transport()
        window.search_changed(NOTHING_MATCHES)
        window.show_playing_album()
        assert window.statusBar().currentMessage() == PLAYING_HIDDEN
        assert window._search.phrase == NOTHING_MATCHES, "the search is kept"
