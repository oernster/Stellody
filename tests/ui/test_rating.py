"""Rating a track on its row, then counting a track that plays out.

The halves a headless run can settle: that a rating given to a row reaches the
store and comes back on that row; also that a count reaches the row under the
library. How a press or a key turns into a rating is in test_star_column.py.
Whether stars in a column read as a rating rather than as decoration needs eyes.
"""

from __future__ import annotations

import pytest
from library_support import ART, PLANETS, SIMPLE
from mouse_support import press_at
from PySide6.QtCore import QModelIndex, Qt
from PySide6.QtWidgets import QApplication
from recording_player import RecordingPlayer
from tray_support import RememberingStore, build

from stellody.domain.listening import (
    MAXIMUM_STARS,
    NO_STARS,
    album_handle,
    track_handle,
)
from stellody.ui.row_text import STARS_ROLE, Column
from stellody.ui.stars import PANEL_MARGIN_PX, STAR_GAP_PX, STAR_PX, StarRating


@pytest.fixture
def player() -> RecordingPlayer:
    """The device, held so a test can say a track has played out."""
    return RecordingPlayer()


@pytest.fixture
def window(application: QApplication, player: RecordingPlayer):
    """A window over a library of two albums, as a load reaches it."""
    made = build(RememberingStore(), player)
    made.show_library((PLANETS, SIMPLE), ART)
    application.processEvents()
    made.resize(900, 700)
    yield made
    made.close()


def _cell(window, row: int, track_row: int, column: Column = Column.STARS):
    """One cell of one track row."""
    album = window._model.index(row, Column.TITLE, QModelIndex())
    return window._model.index(track_row, column, album)


class TestRatingARow:
    def test_a_rating_reaches_the_log_and_the_row(self, window) -> None:
        assert window.rate_track(_cell(window, 0, 0), MAXIMUM_STARS)
        handle = track_handle(PLANETS.identity, 1, 1)
        assert window._listening.of(handle).stars == MAXIMUM_STARS
        assert _cell(window, 0, 0).data(STARS_ROLE) == MAXIMUM_STARS

    def test_two_tracks_are_rated_apart(self, window) -> None:
        window.rate_track(_cell(window, 0, 0), 2)
        window.rate_track(_cell(window, 0, 1), 4)
        assert window._listening.of(track_handle(PLANETS.identity, 1, 1)).stars == 2
        assert window._listening.of(track_handle(PLANETS.identity, 1, 2)).stars == 4

    def test_a_track_never_played_can_be_rated(self, window) -> None:
        """The whole point of it: nothing has to be heard to be judged."""
        window.rate_track(_cell(window, 1, 0), 5)
        record = window._listening.of(track_handle(SIMPLE.identity, 1, 1))
        assert record.stars == 5
        assert record.plays == 0

    def test_an_album_row_rates_nothing(self, window) -> None:
        album = window._model.index(0, Column.STARS, QModelIndex())
        assert window.rate_track(album, 3) is False
        assert album.data(STARS_ROLE) is None
        assert window._listening.of(album_handle(PLANETS.identity)).is_empty

    def test_the_row_says_it_in_words_as_well(self, window) -> None:
        cell = _cell(window, 0, 0)
        assert cell.data(Qt.ItemDataRole.ToolTipRole) == "Not rated"
        window.rate_track(cell, 1)
        assert cell.data(Qt.ItemDataRole.ToolTipRole) == "Rated 1 star out of 5"
        window.rate_track(cell, 3)
        assert cell.data(Qt.ItemDataRole.ToolTipRole) == "Rated 3 stars out of 5"

    def test_the_row_is_redrawn_when_the_rating_changes(self, window) -> None:
        """Otherwise the rating is right and the screen is not."""
        seen: list = []
        window._model.dataChanged.connect(
            lambda first, last, roles: seen.append((first.column(), last.column()))
        )
        window.rate_track(_cell(window, 0, 0), 2)
        assert any(first <= Column.STARS <= last for first, last in seen)

    def test_the_row_under_the_library_carries_no_stars(self, window) -> None:
        """Moved into the column; one home for a track's rating."""
        assert not hasattr(window._position_bar, "stars")


class TestCountingAPlay:
    def test_a_track_that_plays_out_is_counted(self, window, player) -> None:
        window.play_album(PLANETS)
        player.finished = True
        window._poll_transport()
        handle = track_handle(PLANETS.identity, 1, 1)
        assert window._listening.of(handle).plays == 1

    def test_the_count_is_shown_under_the_library(self, window, player) -> None:
        """An album of one track, so the row is still about it afterwards.

        A longer album moves on the moment the track ends, which is right: the
        row is about what is playing now rather than what just stopped.
        """
        window.play_album(SIMPLE)
        assert window._position_bar.plays.text() == ""
        player.finished = True
        window._poll_transport()
        assert window._position_bar.plays.text() == "1 play"

    def test_the_row_moves_on_with_the_music(self, window, player) -> None:
        """What just ended is counted; what the row shows is what plays next."""
        window.play_album(PLANETS)
        player.finished = True
        window._poll_transport()
        assert window._transport.current is PLANETS.tracks[1]
        assert window._position_bar.plays.text() == ""
        assert window._listening.of(track_handle(PLANETS.identity, 1, 1)).plays == 1

    def test_skipping_a_track_counts_nothing(self, window) -> None:
        window.play_album(PLANETS)
        window.next_track()
        handle = track_handle(PLANETS.identity, 1, 1)
        assert window._listening.of(handle).plays == 0

    def test_a_rating_survives_being_counted(self, window, player) -> None:
        window.play_album(PLANETS)
        window.rate_track(_cell(window, 0, 0), 4)
        player.finished = True
        window._poll_transport()
        record = window._listening.of(track_handle(PLANETS.identity, 1, 1))
        assert record == record.__class__(stars=4, plays=1)


class TestTheStarsThemselves:
    def _pressed(self, stars: StarRating, position: int) -> None:
        """A press in the middle of one star, counting from nought."""
        from PySide6.QtCore import QPointF

        x = PANEL_MARGIN_PX + position * (STAR_PX + STAR_GAP_PX) + STAR_PX / 2
        stars.mousePressEvent(press_at(QPointF(x, stars.height() / 2)))

    def test_pressing_the_third_star_is_three(self, application: QApplication) -> None:
        stars = StarRating()
        heard: list[int] = []
        stars.chosen.connect(heard.append)
        self._pressed(stars, 2)
        assert stars.stars == 3
        assert heard == [3]

    def test_pressing_the_rating_it_holds_takes_it_back(
        self, application: QApplication
    ) -> None:
        """Nought is the absence of a rating, so undoing it is the same press."""
        stars = StarRating()
        heard: list[int] = []
        stars.chosen.connect(heard.append)
        self._pressed(stars, 2)
        self._pressed(stars, 2)
        assert stars.stars == NO_STARS
        assert heard == [3, NO_STARS]

    def test_showing_a_rating_reports_nothing(self, application: QApplication) -> None:
        """A track arriving is not somebody saying something about it."""
        stars = StarRating()
        heard: list[int] = []
        stars.chosen.connect(heard.append)
        stars.show_stars(4)
        assert stars.stars == 4
        assert heard == []


class TestRatingTheWholeAlbum:
    """An album is judged whole as well as track by track. The two are
    different answers: a record with one poor track on it is not a poor
    record, so neither is worked out from the other."""

    def _open(self, window, row: int = 0):
        """Open an album under the sleeves, as pressing its cover would."""
        window.toggle_view()
        window.open_album_at(window._model.index(row, Column.TITLE, QModelIndex()))
        return window._album_pane

    def test_the_pane_says_which_rating_it_is(self, window) -> None:
        """It sits inches from the track stars and looks exactly like them."""
        pane = self._open(window)
        assert pane.rating_caption.text() == "Album rating"
        assert "not the track" in pane.album_stars.toolTip()

    def test_rating_it_reaches_the_log(self, window) -> None:
        pane = self._open(window)
        pane.album_stars.chosen.emit(4)
        assert window._listening.of(album_handle(PLANETS.identity)).stars == 4

    def test_it_is_not_the_rating_of_any_track_on_it(self, window) -> None:
        pane = self._open(window)
        pane.album_stars.chosen.emit(4)
        assert window._listening.of(track_handle(PLANETS.identity, 1, 1)).is_empty
        assert window._listening.of(track_handle(PLANETS.identity, 1, 2)).is_empty

    def test_a_track_rating_is_not_the_album_s(self, window) -> None:
        self._open(window)
        window.rate_track(_cell(window, 0, 0), 2)
        assert window._listening.of(album_handle(PLANETS.identity)).is_empty

    def test_it_comes_back_when_the_album_is_opened_again(self, window) -> None:
        pane = self._open(window)
        pane.album_stars.chosen.emit(5)
        window.close_album()
        assert self._open(window).album_stars.stars == 5

    def test_a_different_album_shows_its_own(self, window) -> None:
        pane = self._open(window)
        pane.album_stars.chosen.emit(5)
        window.close_album()
        assert self._open(window, 1).album_stars.stars == NO_STARS

    def test_rating_with_no_album_open_is_harmless(self, window) -> None:
        window.rate_album(3)
        assert window._listening.of(album_handle(PLANETS.identity)).is_empty


class TestTheCountOnTheRows:
    """Where a play count is actually looked for: on the tracks themselves,
    while the library is being read down. The one beside the stars is about a
    single track and is gone the moment that track ends."""

    def _plays(self, window, album_row: int, track_row: int) -> str:
        model = window._model
        album = model.index(album_row, Column.TITLE, QModelIndex())
        return model.data(model.index(track_row, Column.PLAYS, album))

    def test_a_track_nobody_has_played_says_nothing(self, window) -> None:
        """A column of noughts says only that the library is new."""
        assert self._plays(window, 0, 0) == ""

    def test_a_track_that_has_played_says_so(self, window, player) -> None:
        window.play_album(PLANETS)
        player.finished = True
        window._poll_transport()
        assert self._plays(window, 0, 0) == "1 play"

    def test_it_counts_up_on_the_row(self, window) -> None:
        window._listening.rate(track_handle(PLANETS.identity, 1, 1), "a.flac", 0)
        for _ in range(3):
            window._listening.count_play(track_handle(PLANETS.identity, 1, 1), "a.flac")
        assert self._plays(window, 0, 0) == "3 plays"

    def test_the_row_is_redrawn_when_the_count_changes(self, window, player) -> None:
        """Otherwise the number is right and the screen is not."""
        seen: list = []
        window._model.dataChanged.connect(lambda first, last, roles: seen.append(first))
        window.play_album(PLANETS)
        player.finished = True
        window._poll_transport()
        columns = {index.column() for index in seen}
        assert Column.PLAYS in columns

    def test_the_pane_under_the_sleeves_shows_it_too(self, window) -> None:
        """The grid is where this library is mostly read, so it has to be
        there as well as in the list."""
        window.toggle_view()
        window.open_album_at(window._model.index(0, Column.TITLE, QModelIndex()))
        column = window._album_pane.columns[0]
        assert not column.isColumnHidden(Column.PLAYS)
