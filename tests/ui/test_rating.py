"""Rating a track from the stars, then counting a track that plays out.

The two halves a headless run can settle: which track the row is about, then
that what is said about it reaches the store and comes back. Whether five
stars in a rectangle read as a rating rather than as decoration needs eyes.
"""

from __future__ import annotations

import pytest
from conftest import RecordingPlayer
from library_support import ART, PLANETS, SIMPLE
from mouse_support import press_at
from PySide6.QtCore import QModelIndex
from PySide6.QtWidgets import QApplication
from tray_support import RememberingStore, build

from stellody.domain.listening import (
    MAXIMUM_STARS,
    NO_STARS,
    album_handle,
    track_handle,
)
from stellody.ui.row_text import Column
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


def _highlight(window, row: int, track_row: int):
    """Put the highlight on one track of one album, as arrowing to it would."""
    album = window._model.index(row, Column.TITLE, QModelIndex())
    where = window._model.index(track_row, Column.TITLE, album)
    window._tree.setCurrentIndex(where)
    return where


class TestWhichTrackTheRowIsAbout:
    def test_nothing_highlighted_leaves_the_stars_dead(self, window) -> None:
        """A control that cannot mean anything shows no border and is skipped."""
        window.follow_rating()
        assert not window._position_bar.stars.isEnabled()

    def test_it_follows_the_highlight(self, window) -> None:
        _highlight(window, 0, 0)
        window.follow_rating()
        assert window._position_bar.stars.isEnabled()

    def test_what_is_highlighted_wins_over_what_is_playing(self, window) -> None:
        """A track picked out while something else plays is still ratable.

        Deliberately not the rule the shape beside it follows: that is a
        reading of what is audible, while this is a control; a control has
        to be about the thing under the hand.
        """
        window.play_album(PLANETS)
        _highlight(window, 1, 0)
        window.follow_rating()
        window.rate_shown(3)
        assert window._listening.of(track_handle(SIMPLE.identity, 1, 1)).stars == 3
        assert window._listening.of(track_handle(PLANETS.identity, 1, 1)).is_empty

    def test_it_falls_back_to_what_is_playing(self, window) -> None:
        """Nothing pointed at, so the stars answer for the music instead."""
        window.play_album(PLANETS)
        window._tree.setCurrentIndex(QModelIndex())
        window.follow_rating()
        window.rate_shown(2)
        assert window._listening.of(track_handle(PLANETS.identity, 1, 1)).stars == 2

    def test_a_track_never_played_can_be_rated(self, window) -> None:
        """The whole point of it: nothing has to be heard to be judged."""
        _highlight(window, 1, 0)
        window.follow_rating()
        window.rate_shown(5)
        record = window._listening.of(track_handle(SIMPLE.identity, 1, 1))
        assert record.stars == 5
        assert record.plays == 0


class TestRating:
    def test_a_rating_reaches_the_log_and_comes_back(self, window) -> None:
        _highlight(window, 0, 0)
        window.follow_rating()
        window.rate_shown(MAXIMUM_STARS)
        handle = track_handle(PLANETS.identity, 1, 1)
        assert window._listening.of(handle).stars == MAXIMUM_STARS
        assert window._position_bar.stars.stars == MAXIMUM_STARS

    def test_two_tracks_are_rated_apart(self, window) -> None:
        _highlight(window, 0, 0)
        window.rate_shown(2)
        _highlight(window, 0, 1)
        window.follow_rating()
        window.rate_shown(4)
        assert window._listening.of(track_handle(PLANETS.identity, 1, 1)).stars == 2
        assert window._listening.of(track_handle(PLANETS.identity, 1, 2)).stars == 4

    def test_rating_nothing_is_harmless(self, window) -> None:
        window.rate_shown(3)
        assert window._position_bar.stars.stars == NO_STARS

    def test_the_stars_say_it_in_words_as_well(self, window) -> None:
        _highlight(window, 0, 0)
        window.rate_shown(1)
        assert window._position_bar.stars.toolTip() == "Rated 1 star out of 5"
        window.rate_shown(3)
        assert window._position_bar.stars.toolTip() == "Rated 3 stars out of 5"


class TestCountingAPlay:
    def test_a_track_that_plays_out_is_counted(self, window, player) -> None:
        window.play_album(PLANETS)
        player.finished = True
        window._poll_transport()
        handle = track_handle(PLANETS.identity, 1, 1)
        assert window._listening.of(handle).plays == 1

    def test_the_count_is_shown_beside_the_stars(self, window, player) -> None:
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
        window.follow_rating()
        window.rate_shown(4)
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
        window.rate_shown(2)
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

    def _detail(self, window, album_row: int, track_row: int) -> str:
        model = window._model
        album = model.index(album_row, Column.TITLE, QModelIndex())
        return model.data(model.index(track_row, Column.DETAIL, album))

    def test_a_track_nobody_has_played_says_nothing(self, window) -> None:
        """A column of noughts says only that the library is new."""
        assert self._detail(window, 0, 0) == ""

    def test_a_track_that_has_played_says_so(self, window, player) -> None:
        window.play_album(PLANETS)
        player.finished = True
        window._poll_transport()
        assert self._detail(window, 0, 0) == "1 play"

    def test_it_counts_up_on_the_row(self, window) -> None:
        window._listening.rate(track_handle(PLANETS.identity, 1, 1), "a.flac", 0)
        for _ in range(3):
            window._listening.count_play(track_handle(PLANETS.identity, 1, 1), "a.flac")
        assert self._detail(window, 0, 0) == "3 plays"

    def test_the_row_is_redrawn_when_the_count_changes(self, window, player) -> None:
        """Otherwise the number is right and the screen is not."""
        seen: list = []
        window._model.dataChanged.connect(lambda first, last, roles: seen.append(first))
        window.play_album(PLANETS)
        player.finished = True
        window._poll_transport()
        columns = {index.column() for index in seen}
        assert Column.DETAIL in columns

    def test_the_pane_under_the_sleeves_shows_it_too(self, window) -> None:
        """The grid is where this library is mostly read, so it has to be
        there as well as in the list."""
        window.toggle_view()
        window.open_album_at(window._model.index(0, Column.TITLE, QModelIndex()))
        column = window._album_pane.columns[0]
        assert not column.isColumnHidden(Column.DETAIL)
