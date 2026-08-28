"""The auto-scroll cycle, driven by calling the tick rather than by waiting.

The counts below are derived from the constants rather than written out, since
the resume hold is not a whole number of ticks. Waiting five real seconds
instead of driving the tick would be slow and flaky both.
"""

from __future__ import annotations

import math

import pytest
from PySide6.QtWidgets import QApplication, QDialog, QTextBrowser

from stellody.ui import auto_scroller
from stellody.ui.auto_scroller import AutoScroller

LONG_TEXT = "\n".join(f"line {number}" for number in range(400))


def ticks_for(milliseconds: int) -> int:
    """How many ticks a hold takes. The resume hold is not a whole number."""
    return math.ceil(milliseconds / auto_scroller.TICK_MS)


START_TICKS = ticks_for(auto_scroller.START_PAUSE_MS)
BOTTOM_TICKS = ticks_for(auto_scroller.BOTTOM_PAUSE_MS)
RESUME_TICKS = ticks_for(auto_scroller.RESUME_AFTER_MS)


@pytest.fixture(scope="session")
def application() -> QApplication:
    """One real QApplication for the whole session. Qt is never mocked."""
    existing = QApplication.instance()
    return existing or QApplication([])


@pytest.fixture
def surface(application: QApplication) -> QTextBrowser:
    """A text surface whose content overflows, shown offscreen."""
    browser = QTextBrowser()
    browser.setPlainText(LONG_TEXT)
    browser.resize(200, 100)
    browser.show()
    application.processEvents()
    yield browser
    browser.close()


@pytest.fixture
def scroller(surface: QTextBrowser) -> AutoScroller:
    """A scroller whose own timer is stopped, so the test drives every tick."""
    made = AutoScroller(surface)
    assert made.timer.isActive(), "the timer must be running before it is stopped"
    made.timer.stop()
    return made


def run(scroller: AutoScroller, ticks: int) -> None:
    """Drive the cycle by hand."""
    for _ in range(ticks):
        scroller.tick()


def test_a_surface_holds_still_before_its_first_descent(
    scroller: AutoScroller, surface: QTextBrowser
) -> None:
    run(scroller, START_TICKS - 1)
    assert scroller.phase == AutoScroller.PAUSE_TOP
    assert surface.verticalScrollBar().value() == 0


def test_the_descent_begins_once_the_opening_hold_is_spent(
    scroller: AutoScroller,
) -> None:
    run(scroller, START_TICKS)
    assert scroller.phase == AutoScroller.DOWN


def test_the_descent_advances_one_step_every_second_tick(
    scroller: AutoScroller, surface: QTextBrowser
) -> None:
    run(scroller, START_TICKS)
    steps = 20
    run(scroller, steps * auto_scroller.DOWN_TICKS_PER_STEP)
    assert surface.verticalScrollBar().value() == steps * auto_scroller.DOWN_STEP_PX


def test_a_surface_that_fits_never_moves(
    application: QApplication, surface: QTextBrowser
) -> None:
    surface.setPlainText("one line")
    application.processEvents()
    made = AutoScroller(surface)
    made.timer.stop()
    run(made, START_TICKS * 2)
    assert surface.verticalScrollBar().value() == 0


def test_reading_by_hand_suspends_rather_than_disabling(
    scroller: AutoScroller,
) -> None:
    run(scroller, START_TICKS)
    scroller.suspend()
    assert scroller.phase == AutoScroller.MANUAL
    run(scroller, RESUME_TICKS - 1)
    assert scroller.phase == AutoScroller.MANUAL
    run(scroller, 1)
    assert scroller.phase == AutoScroller.DOWN


def test_it_resumes_from_where_the_reader_stopped(
    scroller: AutoScroller, surface: QTextBrowser
) -> None:
    run(scroller, START_TICKS)
    surface.verticalScrollBar().setValue(50)
    scroller.suspend()
    run(scroller, RESUME_TICKS)
    assert surface.verticalScrollBar().value() == 50


def test_a_reader_left_at_the_end_rewinds_because_it_is_the_only_way_on(
    scroller: AutoScroller, surface: QTextBrowser
) -> None:
    run(scroller, START_TICKS)
    bar = surface.verticalScrollBar()
    bar.setValue(bar.maximum())
    scroller.suspend()
    run(scroller, RESUME_TICKS)
    assert scroller.phase == AutoScroller.UP


def test_the_end_is_held_before_the_rewind_takes_it_away(
    scroller: AutoScroller, surface: QTextBrowser
) -> None:
    run(scroller, START_TICKS)
    bar = surface.verticalScrollBar()
    bar.setValue(bar.maximum() - 1)
    run(scroller, auto_scroller.DOWN_TICKS_PER_STEP)
    assert scroller.phase == AutoScroller.PAUSE_BOTTOM
    run(scroller, BOTTOM_TICKS)
    assert scroller.phase == AutoScroller.UP


def test_the_rewind_travels_faster_than_the_reading_pass(
    scroller: AutoScroller, surface: QTextBrowser
) -> None:
    assert auto_scroller.UP_STEP_PX > auto_scroller.DOWN_STEP_PX
    run(scroller, START_TICKS)
    bar = surface.verticalScrollBar()
    bar.setValue(bar.maximum())
    run(scroller, auto_scroller.DOWN_TICKS_PER_STEP + BOTTOM_TICKS)
    assert scroller.phase == AutoScroller.UP
    before = bar.value()
    run(scroller, 1)
    assert before - bar.value() == auto_scroller.UP_STEP_PX


def test_the_dialogs_own_opening_focus_is_not_a_reader(
    scroller: AutoScroller, surface: QTextBrowser
) -> None:
    """Else the long opening stillness becomes the short manual one."""
    scroller._on_focus_changed(None, surface)
    assert scroller.phase == AutoScroller.PAUSE_TOP
    run(scroller, START_TICKS)
    scroller._on_focus_changed(None, surface)
    assert scroller.phase == AutoScroller.MANUAL


def test_a_frozen_surface_consumes_no_time_and_takes_no_input(
    scroller: AutoScroller, surface: QTextBrowser, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A modal above it must leave phase, position and hold exactly as they were."""
    run(scroller, START_TICKS)
    surface.verticalScrollBar().setValue(30)
    other = QDialog()
    monkeypatch.setattr(QApplication, "activeModalWidget", staticmethod(lambda: other))
    scroller.suspend()
    run(scroller, START_TICKS)
    assert scroller.phase == AutoScroller.DOWN
    assert surface.verticalScrollBar().value() == 30
    other.close()
