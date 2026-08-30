"""Measuring a shape without making the window wait and without racing it.

A listener skipping through an album asks for several shapes in a row while
each measurement is still running. Only the last is wanted: an answer for a
track that is no longer playing must never be drawn over the one that is.

The thread is real. Qt is never mocked, so what is stood in for is the
measuring, which would otherwise decode a file.
"""

from __future__ import annotations

import pytest
from PySide6.QtWidgets import QApplication

from stellody.domain.track import TrackSource
from stellody.domain.waveform import Envelope
from stellody.ui.shape_worker import ShapeRunner

FIRST = TrackSource(path="first.flac")
SECOND = TrackSource(path="second.flac")
SHAPE = Envelope(peaks=(0.2, 0.8))


class SlowShapes:
    """Measuring, stood in for. It answers with the path it was asked about."""

    def __init__(self, answer: Envelope | None = SHAPE) -> None:
        self.answer = answer
        self.asked: list[str] = []

    def measured(self, source: TrackSource) -> Envelope | None:
        """Record the ask and answer at once."""
        self.asked.append(source.path)
        return self.answer


class FailingShapes:
    """Measuring, gone wrong."""

    def measured(self, source: TrackSource) -> Envelope | None:
        """Raise, as a decoder meeting something it cannot read would."""
        raise RuntimeError("the file went away mid measurement")


@pytest.fixture
def arrived() -> list[tuple[TrackSource, Envelope | None]]:
    """Every shape the runner passed on."""
    return []


def _runner(shapes, arrived) -> ShapeRunner:
    """A runner reporting into a list."""
    made = ShapeRunner(shapes)
    made.ready.connect(lambda source, shape: arrived.append((source, shape)))
    return made


def test_a_measurement_reaches_the_window(application: QApplication, arrived) -> None:
    runner = _runner(SlowShapes(), arrived)
    runner.measure(FIRST)
    runner.wait()
    application.processEvents()
    assert arrived == [(FIRST, SHAPE)]
    runner.stop()


def test_a_measurement_dropped_before_it_starts_is_never_taken(
    application: QApplication, arrived
) -> None:
    """Skipping quickly through an album should decode nothing it passes."""
    shapes = SlowShapes()
    runner = _runner(shapes, arrived)
    runner.measure(FIRST)
    runner.measure(SECOND)
    runner.wait()
    application.processEvents()
    assert shapes.asked == [SECOND.path]
    assert [source for source, _ in arrived] == [SECOND]
    runner.stop()


def test_an_answer_arriving_after_the_track_changed_is_dropped(
    application: QApplication, arrived
) -> None:
    """Otherwise skipping through an album draws the wrong picture.

    Both measurements run here: the first finishes and its answer is waiting
    to cross back when what is wanted changes underneath it. That is the only
    ordering in which the check on the source has anything to do.
    """
    shapes = SlowShapes()
    runner = _runner(shapes, arrived)
    runner.measure(FIRST)
    runner.wait()
    runner.measure(SECOND)
    runner.wait()
    application.processEvents()
    assert shapes.asked == [FIRST.path, SECOND.path]
    assert [source for source, _ in arrived] == [SECOND]
    runner.stop()


def test_a_measurement_that_raises_says_nothing_rather_than_ending_the_run(
    application: QApplication, arrived
) -> None:
    """It runs on a thread with nobody above it to catch anything."""
    runner = _runner(FailingShapes(), arrived)
    runner.measure(FIRST)
    runner.wait()
    application.processEvents()
    assert arrived == [(FIRST, None)]
    runner.stop()


def test_a_file_with_no_shape_is_reported_as_having_none(
    application: QApplication, arrived
) -> None:
    """So the bar can stop waiting and leave its flat line alone."""
    runner = _runner(SlowShapes(answer=None), arrived)
    runner.measure(FIRST)
    runner.wait()
    application.processEvents()
    assert arrived == [(FIRST, None)]
    runner.stop()


def test_stopping_is_safe_when_nothing_is_running(application: QApplication) -> None:
    """It runs on the way out, where a fault would be the last thing said."""
    runner = ShapeRunner(SlowShapes())
    runner.stop()
    runner.stop()
    assert not runner.running


def test_waiting_is_safe_when_nothing_is_running(application: QApplication) -> None:
    ShapeRunner(SlowShapes()).wait()
