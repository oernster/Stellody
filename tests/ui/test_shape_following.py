"""Which track the bar draws, then when its shape gets measured.

A track that has never been played used to draw a flat line until somebody
pressed play, which says nothing about a track they are deciding whether to
play. So the bar follows the highlight while nothing is loaded.

The measuring is what makes that delicate. A decode is expensive, so stepping
down a list starts one per row and abandons all but the last. What makes that
affordable is measured elsewhere: a measurement gives up at the next block it
reads; letting go of one never waits. These pin what is drawn, then that a
highlight measures at once rather than after a pause.

The shapes service is stood in for. Qt is not.
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
# Comfortably under the two seconds the old blocking wait cost, comfortably
# over anything a handful of instructions takes.
BLOCK_ALLOWANCE_SECONDS = 0.5


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

    def measured(self, source: TrackSource, cancelled=None) -> Envelope | None:
        """The measurement a decode would produce, without decoding.

        The give-up check is taken and honoured, since a stand-in that ignores
        it would let a measurement look unstoppable in every test here.
        """
        self.measured_paths.append(source.path)
        if cancelled is not None and cancelled():
            return None
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
    def test_a_highlighted_track_is_measured_at_once(
        self, application: QApplication
    ) -> None:
        """It waited 400ms first, which was felt and bought nothing.

        The reason for waiting was that a decode per row passed over would be
        wasteful. Measured, the cost was not the decodes: it was letting go of
        one, which blocked the interface thread for two seconds. That is fixed
        where it belongs, so nothing has to be held back here.
        """
        shapes = RecordingShapes()
        window = _window(shapes)
        try:
            _highlight(window, 0)
            window.follow_shape()
            _settle(window, application, wanting=lambda: shapes.measured_paths)
            assert shapes.measured_paths == ["1.flac"]
        finally:
            window.close()

    def test_the_highlight_moving_reaches_the_bar_without_the_poll(
        self, application: QApplication
    ) -> None:
        """The poll runs four times a second, which was a visible beat."""
        shapes = RecordingShapes({"1.flac": SHAPE})
        window = _window(shapes)
        try:
            window._transport_timer.stop()
            _highlight(window, 0)
            assert window._position_bar.slider._shape == SHAPE
        finally:
            window.close()

    def test_the_row_moved_on_from_is_given_up_on(
        self, application: QApplication
    ) -> None:
        """Its answer is dropped, so what is drawn is the row stopped on."""
        shapes = RecordingShapes({"2.flac": OTHER})
        window = _window(shapes)
        try:
            _highlight(window, 0)
            window.follow_shape()
            _highlight(window, 1)
            window.follow_shape()
            _settle(window, application)
            assert window._position_bar.slider._shape == OTHER
        finally:
            window.close()

    def test_letting_go_of_a_measurement_does_not_block(
        self, application: QApplication
    ) -> None:
        """Measured: waiting here froze the window for two seconds a step."""
        shapes = RecordingShapes()
        window = _window(shapes)
        try:
            _highlight(window, 0)
            window.follow_shape()
            began = time.monotonic()
            _highlight(window, 1)
            window.follow_shape()
            assert time.monotonic() - began < BLOCK_ALLOWANCE_SECONDS
        finally:
            window.close()

    def test_a_loaded_track_is_measured_too(self, application: QApplication) -> None:
        shapes = RecordingShapes()
        window = _window(shapes)
        try:
            window.play_album(album())
            window.follow_shape()
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
            assert shapes.measured_paths == []
            assert window._position_bar.slider._shape == SHAPE
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
