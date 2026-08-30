"""Measuring a track's shape without making anybody wait for it.

Measuring decodes the whole file, which takes long enough that doing it on the
interface thread would freeze the window every time a track started. So it
runs on a thread of its own and the shape arrives when it arrives; until then
the bar draws a flat line and behaves exactly as it did before.

A listener who skips through an album asks for several shapes in a row, as
does one simply moving down the library, since the bar draws whatever is
highlighted. Only the last one is wanted, so a result for anything other than
the track in hand is dropped rather than drawn over the top of what is showing
now.

**Letting go of a measurement never waits for it.** Measured, replacing one
mid-decode used to block the interface thread for the full two seconds of the
wait below, because `quit` cannot interrupt a decode: every step through the
library froze the window. The measurement is now told to give up, which it does
at the next block it reads; the thread is set aside rather than waited on.
A thread that has not finished is held rather than forgotten, since Qt ends the
process over a running thread that is destroyed.
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
        self._cancelled = False

    def cancel(self) -> None:
        """Give up at the next block read; say nothing when you do."""
        self._cancelled = True

    @Slot()
    def run(self) -> None:
        """Measure, then say so. A file that cannot be measured says None.

        Nothing here may raise. It runs on a thread with nobody above it to
        catch anything; a picture that cannot be drawn is not a reason to
        take the application down.
        """
        try:
            shape = self._shapes.measured(self._source, lambda: self._cancelled)
        except Exception:  # noqa: BLE001 - a drawing must not end the run
            shape = None
        if not self._cancelled:
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
        self._retired: list[QThread] = []

    @property
    def running(self) -> bool:
        """True while a measurement is in flight."""
        return self._thread is not None

    @property
    def retired(self) -> int:
        """How many measurements were set aside before they had finished."""
        return len(self._retired)

    def measure(self, source: TrackSource) -> None:
        """Measure this track's file, dropping whatever was being measured.

        This returns at once. It is called every time the highlight moves, so
        anything that waited here would be a freeze somebody feels while
        arrowing down a list.
        """
        self._wanted = source
        self.let_go()
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

    def let_go(self) -> None:
        """Tell a measurement in flight to give up, without waiting for it."""
        worker, thread = self._worker, self._thread
        self._thread = None
        self._worker = None
        if worker is not None:
            worker.cancel()
        if thread is not None:
            thread.quit()
            self._retired.append(thread)

    def stop(self) -> None:
        """Let go of everything and wait for it, on the way out."""
        self.let_go()
        self._retired = [thread for thread in self._retired if not thread.wait(WAIT_MS)]

    def wait(self, milliseconds: int = WAIT_MS) -> None:
        """Block until the measurement finishes. For shutdown and for tests."""
        thread = self._thread
        if thread is not None:
            thread.quit()
            thread.wait(milliseconds)

    @Slot(object, object)
    def _on_measured(self, source: TrackSource, shape: Envelope | None) -> None:
        """Pass on a shape, unless it belongs to a track nobody is showing."""
        self._finished()
        if source == self._wanted:
            self.ready.emit(source, shape)

    def _finished(self) -> None:
        """Release a measurement that ran to its own end.

        Held apart from letting one go: there is nothing to stop here and
        nothing to drop, the answer having already been given. Without it the
        runner reports itself busy for the rest of the session and keeps a
        thread for every track ever measured.
        """
        thread = self._thread
        self._thread = None
        self._worker = None
        if thread is not None:
            thread.quit()
            thread.wait(WAIT_MS)
        self._retired = [held for held in self._retired if not held.wait(0)]
