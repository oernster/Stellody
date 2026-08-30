"""The bar that says where a track has reached and moves within it.

What it draws is provisional: the plan wants a waveform with a line crossing
it rather than a groove filling up. What it DOES is not provisional, so these
pin the parts that outlive the drawing: the arithmetic from a point along the
groove to a frame, the clock either side of it, then the rule that a poll
never takes the handle away from somebody holding it.
"""

from __future__ import annotations

import pytest
from PySide6.QtCore import QEvent, QPointF, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QApplication

from stellody.domain.playback import PlaybackPosition
from stellody.domain.track import CD_SAMPLE_RATE
from stellody.ui.position_bar import GROOVE_STEPS, NO_POSITION_TEXT, PositionBar

TRACK_SECONDS = 200
TRACK_FRAMES = CD_SAMPLE_RATE * TRACK_SECONDS


@pytest.fixture
def asked() -> list[int]:
    """Every frame the bar asked the transport to move to."""
    return []


@pytest.fixture
def bar(application: QApplication, asked: list[int]) -> PositionBar:
    """A bar whose seeking is recorded rather than played."""
    made = PositionBar(seek=asked.append)
    made.resize(400, 40)
    yield made
    made.deleteLater()


def _at(seconds: int) -> PlaybackPosition:
    """Where playback would be, that many seconds in."""
    return PlaybackPosition(
        frame=CD_SAMPLE_RATE * seconds,
        frame_count=TRACK_FRAMES,
        sample_rate=CD_SAMPLE_RATE,
    )


def test_with_nothing_playing_it_says_nothing_and_offers_nothing(bar) -> None:
    bar.show_position(None)
    assert bar.clock.text() == NO_POSITION_TEXT
    assert not bar.slider.isEnabled(), "there is nowhere to move to"


def test_it_shows_how_far_in_and_how_long(bar) -> None:
    bar.show_position(_at(67))
    assert bar.clock.text() == "1:07 / 3:20"
    assert bar.slider.isEnabled()


def test_halfway_through_sits_halfway_along(bar) -> None:
    bar.show_position(_at(TRACK_SECONDS // 2))
    assert bar.slider.value() == GROOVE_STEPS // 2


def test_the_end_of_the_track_is_the_end_of_the_groove(bar) -> None:
    """And never past it, whatever a lead correction has done to the figure."""
    bar.show_position(
        PlaybackPosition(
            frame=TRACK_FRAMES * 2,
            frame_count=TRACK_FRAMES,
            sample_rate=CD_SAMPLE_RATE,
        )
    )
    assert bar.slider.value() == GROOVE_STEPS


def test_a_track_of_no_length_offers_no_seeking(bar) -> None:
    """A stream still opening reports a count of nothing; it is not a place."""
    bar.show_position(
        PlaybackPosition(frame=0, frame_count=0, sample_rate=CD_SAMPLE_RATE)
    )
    assert not bar.slider.isEnabled()
    assert bar.slider.value() == 0


def test_letting_go_moves_the_music_to_where_the_handle_was_left(bar, asked) -> None:
    """The whole point of it: a click three quarters along means that."""
    bar.show_position(_at(0))
    bar.slider.setValue(GROOVE_STEPS * 3 // 4)
    bar.slider.sliderReleased.emit()
    assert asked == [TRACK_FRAMES * 3 // 4]


def test_dragging_moves_the_clock_without_moving_the_music(bar, asked) -> None:
    """So the figure follows the handle while it is being aimed."""
    bar.show_position(_at(0))
    bar.slider.sliderMoved.emit(GROOVE_STEPS // 4)
    assert bar.clock.text() == "0:50 / 3:20"
    assert asked == [], "nothing moves until the handle is let go"


def test_a_poll_never_takes_the_handle_from_somebody_holding_it(bar) -> None:
    """Otherwise aiming at a point drags itself back four times a second."""
    bar.show_position(_at(0))
    bar.slider.setSliderDown(True)
    bar.slider.setValue(GROOVE_STEPS // 2)
    bar.show_position(_at(1))
    assert bar.slider.value() == GROOVE_STEPS // 2, "the drag was left alone"
    bar.slider.setSliderDown(False)


def test_letting_go_of_a_track_of_no_length_asks_for_nothing(bar, asked) -> None:
    """There is nothing to move within, so there is nothing to say."""
    bar.show_position(None)
    bar.slider.sliderReleased.emit()
    assert asked == []


def test_the_bar_itself_is_never_a_focus_stop(bar) -> None:
    """A ring belongs to a control; the strip holding one is not a control."""
    assert not bar.focusPolicy()


def test_clicking_the_groove_goes_there_rather_than_nudging_a_page(bar) -> None:
    """Qt's own answer to a click on the groove is one page further on.

    Somebody clicking three quarters of the way along a track means three
    quarters of the way along, which is the whole reason for reaching for this
    control at all.
    """
    bar.show_position(_at(0))
    bar.show()
    click = QMouseEvent(
        QEvent.Type.MouseButtonPress,
        QPointF(bar.slider.width() * 3 / 4, bar.slider.height() / 2),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    bar.slider.mousePressEvent(click)
    assert bar.slider.value() > GROOVE_STEPS // 2, "it went where it was clicked"
    bar.hide()


def test_a_click_that_is_not_the_left_button_is_left_to_qt(bar) -> None:
    """Nothing here has an opinion about the other buttons."""
    bar.show_position(_at(0))
    bar.show()
    before = bar.slider.value()
    click = QMouseEvent(
        QEvent.Type.MouseButtonPress,
        QPointF(bar.slider.width() * 3 / 4, bar.slider.height() / 2),
        Qt.MouseButton.RightButton,
        Qt.MouseButton.RightButton,
        Qt.KeyboardModifier.NoModifier,
    )
    bar.slider.mousePressEvent(click)
    assert bar.slider.value() == before
    bar.hide()
