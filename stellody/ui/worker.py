"""Running a library scan off the interface thread.

Progress and results cross back as Qt signals, which are delivered on the
receiving object's own thread. The receiver is always a bound method of a
QObject living on the interface thread, never a bare callable, because a signal
connected to a bare callable runs in the sender's thread instead.
"""

from __future__ import annotations

from PySide6.QtCore import QObject, QThread, Signal, Slot

from stellody.application.scan import ScanLibrary, ScanProgress, ScanReport

# Long enough for the folder being read when the cancel arrives, short enough
# that a scan wedged on an unresponsive drive cannot hold the quit for ever.
WAIT_MS = 5000


class ScanWorker(QObject):
    """Performs one scan and reports what happened.

    The cancel flag is a plain attribute read by the scanning thread and
    written by the interface thread. Nothing else touches it, the write is a
    single store of True and a stale read costs one more folder, so no lock is
    needed for it to do its job.
    """

    progressed = Signal(object)
    completed = Signal(object)
    failed = Signal(str)

    def __init__(self, scanner: ScanLibrary, root: str) -> None:
        super().__init__()
        self._scanner = scanner
        self._root = root
        self._cancelled = False

    def cancel(self) -> None:
        """Ask the scan to stop at the next folder boundary."""
        self._cancelled = True

    @Slot()
    def run(self) -> None:
        """Scan the root, emitting progress and then the report."""
        try:
            report = self._scanner.run(
                self._root,
                progress=self.progressed.emit,
                cancelled=lambda: self._cancelled,
            )
        except OSError as error:
            self.failed.emit(str(error))
            return
        self.completed.emit(report)


class ScanRunner(QObject):
    """Owns the worker thread and keeps its lifetime tidy."""

    progressed = Signal(object)
    completed = Signal(object)
    failed = Signal(str)
    stopped = Signal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._thread: QThread | None = None
        self._worker: ScanWorker | None = None

    @property
    def running(self) -> bool:
        """True while a scan is in flight."""
        return self._thread is not None

    def start(self, scanner: ScanLibrary, root: str) -> bool:
        """Begin a scan; False when one is already running."""
        if self._thread is not None:
            return False
        thread = QThread(self)
        worker = ScanWorker(scanner, root)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.progressed.connect(self._on_progress)
        worker.completed.connect(self._on_completed)
        worker.failed.connect(self._on_failed)
        self._thread = thread
        self._worker = worker
        thread.start()
        return True

    def cancel(self) -> None:
        """Ask a running scan to give up. Harmless when none is running."""
        worker = self._worker
        if worker is not None:
            worker.cancel()

    def wait(self, milliseconds: int = WAIT_MS) -> None:
        """Block until the running scan finishes. For shutdown and for tests.

        Qt cannot interrupt a slot that is already running, so quitting the
        thread does nothing at all while a scan is in flight: it is the cancel
        that ends it. Waiting without cancelling first froze the window for
        the whole of the wait, which is what a mid-scan quit used to do.
        """
        thread = self._thread
        if thread is not None:
            self.cancel()
            thread.quit()
            thread.wait(milliseconds)

    @Slot(object)
    def _on_progress(self, progress: ScanProgress) -> None:
        """Relay progress on the interface thread."""
        self.progressed.emit(progress)

    @Slot(object)
    def _on_completed(self, report: ScanReport) -> None:
        """Relay the report, then tear the thread down."""
        self._finish()
        self.completed.emit(report)

    @Slot(str)
    def _on_failed(self, message: str) -> None:
        """Relay a failure, then tear the thread down."""
        self._finish()
        self.failed.emit(message)

    def _finish(self) -> None:
        """Stop the thread and release both it and the worker."""
        thread = self._thread
        self._thread = None
        self._worker = None
        if thread is not None:
            thread.quit()
            thread.wait()
            thread.deleteLater()
        self.stopped.emit()
