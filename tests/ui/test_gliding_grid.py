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
from PySide6.QtCore import QAbstractAnimation
from PySide6.QtWidgets import QAbstractItemView, QApplication
from tray_support import RememberingStore, build

from stellody.ui.gliding import GLIDE_MS, GlidingGrid

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
