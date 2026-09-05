"""The sleeve grid travels to a selection instead of snapping to it.

Time is never waited on here. An animation is driven by setting its current
time, so what is asserted is the run itself, where it starts, where it ends and
that the scrollbar follows it, rather than whatever a sleep happened to catch.
A test that sleeps for an animation is a test that fails on a busy machine.

What is NOT asserted is that the result looks smooth. Nothing offscreen can see
paint. What can be settled here is the mechanism: the scrollbar counts in
pixels rather than in rows; the value moves through the distance instead of
arriving at the far end in one step.
"""

from __future__ import annotations

import pytest
from conftest import RecordingPlayer
from library_support import track
from PySide6.QtCore import QAbstractAnimation, QPoint, QPointF, Qt
from PySide6.QtGui import QWheelEvent
from PySide6.QtWidgets import QAbstractItemView, QApplication
from tray_support import RememberingStore, build

from stellody.domain.album import Album
from stellody.domain.identity import AlbumIdentity
from stellody.ui.gliding import GLIDE_MS, NOTCH, GlidingGrid

# Far enough down that revealing it has to move the grid at all.
SCROLL_TARGET_PX = 400


@pytest.fixture
def grid(application: QApplication):
    """The real grid, shown, over a window that holds one album."""
    made = build(RememberingStore(), RecordingPlayer(), leave=lambda: None)
    made.show()
    application.processEvents()
    yield made._grid
    made.close()


def test_the_grid_counts_its_scrolling_in_pixels_not_in_rows(grid) -> None:
    """A view counting in items cannot move by less than a whole row.

    This is the jerk itself rather than a proxy for it: with the default mode
    the smallest move the grid could make was one row of sleeves tall.
    """
    assert isinstance(grid, GlidingGrid)
    per_pixel = QAbstractItemView.ScrollMode.ScrollPerPixel
    assert grid.verticalScrollMode() == per_pixel
    assert grid.horizontalScrollMode() == per_pixel


def test_a_reveal_travels_the_distance_rather_than_arriving_at_it(grid) -> None:
    """The scrollbar is put back to where it was, then walked to the target."""
    bar = grid.verticalScrollBar()
    bar.setRange(0, SCROLL_TARGET_PX)
    bar.setValue(0)
    grid.glide.setStartValue(0)
    grid.glide.setEndValue(SCROLL_TARGET_PX)
    grid.glide.start()
    assert grid.glide.state() == QAbstractAnimation.State.Running

    grid.glide.setCurrentTime(GLIDE_MS // 2)
    halfway = bar.value()
    assert 0 < halfway < SCROLL_TARGET_PX, "part way, not at either end"

    grid.glide.setCurrentTime(GLIDE_MS)
    assert bar.value() == SCROLL_TARGET_PX, "and all the way by the end"


def test_a_reveal_that_moves_nothing_starts_no_run(grid) -> None:
    """An album already on screen is not worth animating to."""
    grid.scrollTo(grid.model().index(0, 0))
    assert grid.glide.state() == QAbstractAnimation.State.Stopped


def test_an_unseen_grid_arrives_rather_than_travelling(grid) -> None:
    """A view laid out while hidden scrolls for nobody, so it just goes there.

    Otherwise the grid would still be moving at the moment it is shown, which
    is the one time the movement explains nothing.
    """
    bar = grid.verticalScrollBar()
    bar.setRange(0, SCROLL_TARGET_PX)
    grid.hide()
    bar.setValue(SCROLL_TARGET_PX)
    grid.scrollTo(grid.model().index(0, 0))
    assert grid.glide.state() == QAbstractAnimation.State.Stopped


def test_the_run_is_put_on_the_scrollbar_as_it_goes(grid) -> None:
    """The animation carries a number; the scrollbar is what it is for."""
    bar = grid.verticalScrollBar()
    bar.setRange(0, SCROLL_TARGET_PX)
    bar.setValue(0)
    grid._travel(SCROLL_TARGET_PX // 2)
    assert bar.value() == SCROLL_TARGET_PX // 2


# Enough sleeves that the grid has somewhere to scroll to, whatever width the
# offscreen platform decides to lay them out at.
ENOUGH_ALBUMS = 40


@pytest.fixture
def sleeves(application: QApplication):
    """The grid over a library long enough to scroll, with the covers up."""
    made = build(RememberingStore(), RecordingPlayer(), leave=lambda: None)
    made.show_library(
        tuple(
            Album(
                identity=AlbumIdentity(album_artist="Holst", title=f"Album {n:02d}"),
                tracks=(track("One", 1),),
            )
            for n in range(ENOUGH_ALBUMS)
        ),
        (),
    )
    made.toggle_view()
    made.resize(1000, 700)
    made.show()
    application.processEvents()
    yield made._grid
    made.close()


def turn(grid, application: QApplication, eighths: int, pixels: QPoint = None) -> int:
    """Turn the wheel over the grid; how far the scrollbar moved.

    Stated in eighths of a degree because that is the unit Qt reports a wheel
    in: one notch is 120 of them.
    """
    bar = grid.verticalScrollBar()
    before = bar.value()
    application.sendEvent(
        grid.viewport(),
        QWheelEvent(
            QPointF(100, 100),
            QPointF(100, 100),
            pixels or QPoint(0, 0),
            QPoint(0, eighths),
            Qt.MouseButton.NoButton,
            Qt.KeyboardModifier.NoModifier,
            Qt.ScrollPhase.NoScrollPhase,
            False,
        ),
    )
    application.processEvents()
    return bar.value() - before


class TestOneNotchIsOneRow:
    """Measured before this was written: counting the scrollbar in pixels, the
    thing that makes the glide continuous, left Qt scrolling by the item height
    times the system's lines per notch. That was 518 pixels over a 236 pixel
    row, so one detent carried two rows of artwork past the eye and part of a
    third."""

    def test_a_notch_down_moves_exactly_one_row(self, sleeves, application) -> None:
        assert turn(sleeves, application, -NOTCH) == sleeves.gridSize().height()

    def test_a_notch_up_moves_exactly_one_row_back(self, sleeves, application) -> None:
        row = sleeves.gridSize().height()
        turn(sleeves, application, -NOTCH * 2)
        assert turn(sleeves, application, NOTCH) == -row

    def test_two_notches_at_once_move_two_rows(self, sleeves, application) -> None:
        """A wheel spun hard reports several notches in one event."""
        row = sleeves.gridSize().height()
        assert turn(sleeves, application, -NOTCH * 2) == row * 2

    def test_part_of_a_notch_moves_nothing_yet(self, sleeves, application) -> None:
        assert turn(sleeves, application, -NOTCH // 3) == 0

    def test_parts_of_a_notch_add_up_to_a_row(self, sleeves, application) -> None:
        """A wheel that reports in fractions would otherwise lose the
        remainder on every event and never move at all."""
        row = sleeves.gridSize().height()
        moved = sum(turn(sleeves, application, -NOTCH // 2) for _ in range(2))
        assert moved == row

    def test_a_trackpad_is_left_continuous(self, sleeves, application) -> None:
        """It reports a pixel delta and is already smooth, so rounding it to
        whole rows would take away the one thing it does better."""
        row = sleeves.gridSize().height()
        moved = turn(sleeves, application, -NOTCH, pixels=QPoint(0, -8))
        assert moved != row
