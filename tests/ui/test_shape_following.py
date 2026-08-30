"""Which track the bar draws, then when its shape gets measured.

A track that has never been played used to draw a flat line until somebody
pressed play, which says nothing about a track they are deciding whether to
play. So the bar follows the highlight while nothing is loaded.

The measuring is what makes that delicate. A decode is expensive, so stepping
down a list must not set one going for every row passed on the way. These pin
both halves: what is drawn, then what is measured and when.

The shapes service is stood in for. Qt is not: the timer is the real one and
the assertions read its actual state.
"""

from __future__ import annotations

import time

from conftest import RecordingPlayer
from PySide6.QtCore import QModelIndex
from PySide6.QtWidgets import QApplication
from tray_support import RememberingStore, album, build

from stellody.domain.track import TrackSource
from stellody.domain.waveform import Envelope
from stellody.ui.models import Column

SHAPE = Envelope(peaks=(0.2, 0.9, 0.4))
OTHER = Envelope(peaks=(0.5, 0.5, 0.5))
SETTLE_SECONDS = 3.0


class RecordingShapes:
    """A shapes service that answers from a script and remembers being asked."""

    def __init__(self, kept: dict[str, Envelope] | None = None) -> None:
        self.kept = dict(kept or {})
        self.asked: list[str] = []
        self.measured_paths: list[str] = []

    def remembered(self, source: TrackSource) -> Envelope | None:
        """Whatever was measured before; never decodes."""
        self.asked.append(source.path)
        return self.kept.get(source.path)

    def measured(self, source: TrackSource) -> Envelope | None:
        """The measurement a decode would produce, without decoding."""
        self.measured_paths.append(source.path)
        return self.kept.get(source.path, SHAPE)


def _window(shapes: RecordingShapes):
    """A real window over a recording player and those shapes."""
    return build(RememberingStore(), RecordingPlayer(), shapes=shapes)


def _track_index(window, row: int = 0) -> QModelIndex:
    """Where one track sits under the one album."""
    parent = window._model.index(0, Column.TITLE, QModelIndex())
    return window._model.index(row, Column.TITLE, parent)


def _highlight(window, row: int = 0) -> None:
    """Put the highlight on a track, as arrowing on to it would."""
    window._tree.expandAll()
    window._tree.setCurrentIndex(_track_index(window, row))


class TestWhatTheBarDraws:
    def test_a_highlighted_track_shows_its_shape_before_it_plays(
        self, application: QApplication
    ) -> None:
        shapes = RecordingShapes({"1.flac": SHAPE})
        window = _window(shapes)
        try:
            _highlight(window, 0)
            window.follow_shape()
            assert window._position_bar.slider._shape == SHAPE
        finally:
            window.close()

    def test_nothing_highlighted_draws_no_shape(
        self, application: QApplication
    ) -> None:
        window = _window(RecordingShapes())
        try:
            window.follow_shape()
            assert window._position_bar.slider._shape is None
        finally:
            window.close()

    def test_what_is_loaded_wins_over_what_is_highlighted(
        self, application: QApplication
    ) -> None:
        """The playhead belongs to the loaded track, so the shape must too.

        Browsing the library during playback would otherwise swap the picture
        out from under the line crossing it.
        """
        shapes = RecordingShapes({"1.flac": SHAPE, "2.flac": OTHER})
        window = _window(shapes)
        try:
            window.play_album(album())
            window.follow_shape()
            _highlight(window, 1)
            window.follow_shape()
            assert window._position_bar.slider._shape == SHAPE
        finally:
            window.close()


class TestWhenItIsMeasured:
    def test_a_highlighted_track_waits_for_the_highlight_to_settle(
        self, application: QApplication
    ) -> None:
        shapes = RecordingShapes()
        window = _window(shapes)
        try:
            _highlight(window, 0)
            window.follow_shape()
            assert window._shape_settle.isActive()
            assert shapes.measured_paths == [], "nothing decoded yet"
        finally:
            window.close()

    def test_the_row_stopped_on_is_the_one_measured(
        self, application: QApplication
    ) -> None:
        """Stepping past a row must not set a decode going for it."""
        shapes = RecordingShapes()
        window = _window(shapes)
        try:
            _highlight(window, 0)
            window.follow_shape()
            _highlight(window, 1)
            window.follow_shape()
            # The timer's own firing is proved by the test below; this drives
            # the one path, so what it measures is not two things at once.
            window._shape_settle.stop()
            window._measure_settled()
            _settle(window, application)
            assert shapes.measured_paths == ["2.flac"]
        finally:
            window.close()

    def test_the_settling_timer_really_reaches_the_measurement(
        self, application: QApplication
    ) -> None:
        """The timer is left to fire on its own, so the wiring is proved."""
        shapes = RecordingShapes()
        window = _window(shapes)
        try:
            window._shape_settle.setInterval(1)
            _highlight(window, 0)
            window.follow_shape()
            _settle(window, application, wanting=lambda: shapes.measured_paths)
            assert shapes.measured_paths == ["1.flac"]
        finally:
            window.close()

    def test_a_loaded_track_is_measured_without_waiting(
        self, application: QApplication
    ) -> None:
        """Somebody pressed play and is watching the bar."""
        shapes = RecordingShapes()
        window = _window(shapes)
        try:
            window.play_album(album())
            window.follow_shape()
            assert not window._shape_settle.isActive()
            _settle(window, application, wanting=lambda: shapes.measured_paths)
            assert shapes.measured_paths == ["1.flac"]
        finally:
            window.close()

    def test_a_shape_already_measured_costs_no_decode_at_all(
        self, application: QApplication
    ) -> None:
        shapes = RecordingShapes({"1.flac": SHAPE})
        window = _window(shapes)
        try:
            _highlight(window, 0)
            window.follow_shape()
            assert not window._shape_settle.isActive()
            assert shapes.measured_paths == []
        finally:
            window.close()


def _settle(window, application: QApplication, wanting=None) -> None:
    """Let the measuring thread finish and its answer come back."""
    deadline = time.monotonic() + SETTLE_SECONDS
    while time.monotonic() < deadline:
        application.processEvents()
        if wanting is not None and wanting():
            application.processEvents()
            return
        if wanting is None and not window._shape_runner.running:
            return
