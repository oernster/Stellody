"""Measuring a track's shape without making anybody wait for it.

Measuring decodes the whole file, which takes long enough that doing it on the
interface thread would freeze the window every time a track started. So it
runs on a thread of its own and the shape arrives when it arrives; until then
the bar draws a flat line and behaves exactly as it did before.

A listener who skips through an album asks for several shapes in a row. Only
the last one is wanted, so a result for anything other than the track in hand
is dropped rather than drawn over the top of what is playing now.
"""

from __future__ import annotations

from PySide6.QtCore import QObject, QThread, Signal, Slot

from stellody.application.shapes import TrackShapes
from stellody.domain.track import TrackSource
from stellody.domain.waveform import Envelope

# Long enough for a measurement to notice it is not wanted, short enough that
# shutting down never feels like a hang. A measurement is pure reading, so
# abandoning one costs nothing but the reading already done.
WAIT_MS = 2000


class ShapeWorker(QObject):
    """One measurement, run on a thread that is not the interface's."""

    measured = Signal(object, object)

    def __init__(self, shapes: TrackShapes, source: TrackSource) -> None:
        super().__init__()
        self._shapes = shapes
        self._source = source

    @Slot()
    def run(self) -> None:
        """Measure, then say so. A file that cannot be measured says None.

        Nothing here may raise. It runs on a thread with nobody above it to
        catch anything; a picture that cannot be drawn is not a reason to
        take the application down.
        """
        try:
            shape = self._shapes.measured(self._source)
        except Exception:  # noqa: BLE001 - a drawing must not end the run
            shape = None
        self.measured.emit(self._source, shape)


class ShapeRunner(QObject):
    """Keeps one measurement in flight and forgets any answer nobody wants."""

    ready = Signal(object, object)

    def __init__(self, shapes: TrackShapes, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._shapes = shapes
        self._thread: QThread | None = None
        self._worker: ShapeWorker | None = None
        self._wanted: TrackSource | None = None

    @property
    def running(self) -> bool:
        """True while a measurement is in flight."""
        return self._thread is not None

    def measure(self, source: TrackSource) -> None:
        """Measure this track's file, dropping whatever was being measured."""
        self._wanted = source
        self.stop()
        thread = QThread(self)
        worker = ShapeWorker(self._shapes, source)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        # Connected to a bound method of this object, which lives on the
        # interface thread, so the answer crosses back rather than arriving
        # on the measuring thread and drawing from it.
        worker.measured.connect(self._on_measured)
        self._thread = thread
        self._worker = worker
        thread.start()

    def stop(self) -> None:
        """Let go of a measurement in flight. Harmless when there is none."""
        thread = self._thread
        self._thread = None
        self._worker = None
        if thread is not None:
            thread.quit()
            thread.wait(WAIT_MS)

    def wait(self, milliseconds: int = WAIT_MS) -> None:
        """Block until the measurement finishes. For shutdown and for tests."""
        thread = self._thread
        if thread is not None:
            thread.quit()
            thread.wait(milliseconds)

    @Slot(object, object)
    def _on_measured(self, source: TrackSource, shape: Envelope | None) -> None:
        """Pass on a shape, unless it belongs to a track nobody is playing."""
        if source == self._wanted:
            self.ready.emit(source, shape)
