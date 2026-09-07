"""Running a discovery off the interface thread.

A run over a whole library takes about eleven minutes at the rate the
catalogues permit, so it cannot happen on the thread that draws the window.

The same shape as the scan runner beside it, for the same reasons: progress and
results cross back as Qt signals, with every receiver a bound method of a
QObject living on the interface thread rather than a bare callable. A signal
connected to a bare callable runs in the SENDER's thread instead, which is how
a background thread comes to touch a widget.
"""

from __future__ import annotations

from PySide6.QtCore import QObject, QThread, Signal, Slot

from stellody.application.discovering import Discovery
from stellody.application.values import DiscoveryProgress, RunReport
from stellody.domain.album import Album

# Long enough for the request in flight when the cancel arrives, short enough
# that a run wedged on an unresponsive service cannot hold the quit for ever.
# A request's own timeout is shorter than this, so an ordinary cancel is
# noticed well inside it.
WAIT_MS = 30000


class DiscoveryWorker(QObject):
    """Performs one discovery run and reports what happened.

    The cancel flag is a plain attribute read by the running thread and written
    by the interface thread. Nothing else touches it, the write is a single
    store of True and a stale read costs one more request, so no lock is needed
    for it to do its job.
    """

    progressed = Signal(object)
    completed = Signal(object)
    failed = Signal(str)

    def __init__(
        self,
        discovery: Discovery,
        albums: tuple[Album, ...],
        ticked: tuple[str, ...],
    ) -> None:
        super().__init__()
        self._discovery = discovery
        self._albums = albums
        self._ticked = ticked
        self._cancelled = False

    def cancel(self) -> None:
        """Ask the run to stop before its next request."""
        self._cancelled = True

    @Slot()
    def run(self) -> None:
        """Do the run, emitting progress and then the report.

        Every failure is reported rather than only the ones anticipated. A run
        that raised anything else would end the thread in silence, leaving a
        bar spinning against a dialog that never heard another word.
        """
        try:
            report = self._discovery.run(
                self._albums,
                self._ticked,
                self.progressed.emit,
                lambda: self._cancelled,
            )
        except Exception as error:  # noqa: BLE001 - reported, never swallowed
            self.failed.emit(str(error))
            return
        self.completed.emit(report)


class DiscoveryRunner(QObject):
    """Owns the worker thread and keeps its lifetime tidy."""

    progressed = Signal(object)
    completed = Signal(object)
    failed = Signal(str)
    stopped = Signal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._thread: QThread | None = None
        self._worker: DiscoveryWorker | None = None
        # Runs somebody stopped, still winding down. Held so Qt does not
        # destroy a thread that is still running, which ends the process.
        self._abandoned: list[QThread] = []

    @property
    def running(self) -> bool:
        """True while a run is in flight."""
        return self._thread is not None

    def start(
        self,
        discovery: Discovery,
        albums: tuple[Album, ...],
        ticked: tuple[str, ...],
    ) -> bool:
        """Begin a run; False when one is already going."""
        if self._thread is not None:
            return False
        thread = QThread(self)
        worker = DiscoveryWorker(discovery, albums, ticked)
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
        """Give up on a run at once. Harmless when none is running.

        The run is ABANDONED rather than waited for. Ruled on 2026-09-07: a
        stop means stop, so everything a listener can see has to happen now
        rather than when the run gets round to noticing.

        A request already issued cannot be called back. Nothing portable
        interrupts a thread blocked waiting for a socket, while the wait for
        a response happens inside `urlopen` before there is anything to close,
        so the honest choice is between making somebody wait for it and
        letting go of it. This lets go: the thread is moved aside with its
        signals cut, so it reports to nobody and blocks nothing. It ends on
        its own at its next check or when its socket times out.

        The thread is kept rather than dropped. A QThread destroyed while it
        is still running takes the process down with it, so the reference is
        held until the run it carries has actually finished.
        """
        worker, thread = self._worker, self._thread
        self._worker = None
        self._thread = None
        if worker is None or thread is None:
            return
        worker.cancel()
        worker.progressed.disconnect()
        worker.completed.disconnect()
        worker.failed.disconnect()
        # Whatever it ends up saying, it says it to this and nothing else.
        worker.completed.connect(lambda _report: self._abandoned_ended(thread))
        worker.failed.connect(lambda _message: self._abandoned_ended(thread))
        self._abandoned.append(thread)
        self.stopped.emit()

    def _abandoned_ended(self, thread: QThread) -> None:
        """An abandoned run has finished; let go of the thread it was on."""
        thread.quit()
        thread.wait()
        if thread in self._abandoned:
            self._abandoned.remove(thread)
        thread.deleteLater()

    def wait(self, milliseconds: int = WAIT_MS) -> None:
        """Block until every run finishes, abandoned ones included.

        A different thing from a stop, deliberately not built on one. A
        stop lets go of a run because somebody is waiting to carry on using
        the window; this waits for it, because the application is closing and
        a thread still running when Qt tears it down ends the process.

        Qt cannot interrupt a slot already running, so quitting the thread does
        nothing at all while a run is in flight: it is the flag that ends it.
        The run keeps its signals here, so a run that finishes in time still
        reports what it found.
        """
        worker = self._worker
        if worker is not None:
            worker.cancel()
        thread = self._thread
        if thread is not None:
            thread.quit()
            thread.wait(milliseconds)
        for abandoned in tuple(self._abandoned):
            abandoned.quit()
            abandoned.wait(milliseconds)
            if abandoned in self._abandoned:
                self._abandoned.remove(abandoned)

    @Slot(object)
    def _on_progress(self, progress: DiscoveryProgress) -> None:
        """Relay progress on the interface thread."""
        self.progressed.emit(progress)

    @Slot(object)
    def _on_completed(self, report: RunReport) -> None:
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
