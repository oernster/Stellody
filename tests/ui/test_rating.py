"""Rating a track from the stars, then counting a track that plays out.

The two halves a headless run can settle: which track the row is about, then
that what is said about it reaches the store and comes back. Whether five
stars in a rectangle read as a rating rather than as decoration needs eyes.
"""

from __future__ import annotations

import pytest
from conftest import RecordingPlayer
from library_support import ART, PLANETS, SIMPLE
from PySide6.QtCore import QModelIndex, Qt
from PySide6.QtWidgets import QApplication
from tray_support import RememberingStore, build

from stellody.domain.listening import MAXIMUM_STARS, NO_STARS, track_handle
from stellody.ui.models import Column
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
        from PySide6.QtGui import QMouseEvent

        x = PANEL_MARGIN_PX + position * (STAR_PX + STAR_GAP_PX) + STAR_PX / 2
        stars.mousePressEvent(
            QMouseEvent(
                QMouseEvent.Type.MouseButtonPress,
                QPointF(x, stars.height() / 2),
                Qt.MouseButton.LeftButton,
                Qt.MouseButton.LeftButton,
                Qt.KeyboardModifier.NoModifier,
            )
        )

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
