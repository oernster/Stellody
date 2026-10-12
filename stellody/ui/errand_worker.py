"""Running one errand off the interface thread, then answering on it.

A backup, a check of a chosen backup and the staging of a restore each take a
moment on a fast disk and longer on a slow one, so none of them may run where
the window and the sound are fed (BACKUP.md FR-B13). Each is one call with one
answer, which is all this carries.

The answer crosses back as a signal to a slot of this object, which lives on
the interface thread; only then are the callbacks the window gave it called,
so they run where they may touch a widget. A signal connected to a bare
callable would run in the sender's thread instead.
"""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QObject, QThread, Signal, Slot

Errand = Callable[[], object]


class _ErrandWorker(QObject):
    """Performs one errand and reports its answer or what stopped it."""

    answered = Signal(object)
    failed = Signal(object)

    def __init__(self, errand: Errand) -> None:
        super().__init__()
        self._errand = errand

    @Slot()
    def run(self) -> None:
        """Run the errand; EVERY failure is reported, never swallowed."""
        try:
            answer = self._errand()
        except Exception as error:  # noqa: BLE001 - reported, never swallowed
            self.failed.emit(error)
            return
        self.answered.emit(answer)


class ErrandRunner(QObject):
    """Owns the thread one errand runs on, one errand at a time."""

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._thread: QThread | None = None
        self._worker: _ErrandWorker | None = None
        self._on_answer: Callable[[object], None] = _ignored
        self._on_failure: Callable[[Exception], None] = _ignored

    @property
    def running(self) -> bool:
        """True while an errand is in flight."""
        return self._thread is not None

    def start(
        self,
        errand: Errand,
        on_answer: Callable[[object], None],
        on_failure: Callable[[Exception], None],
    ) -> bool:
        """Begin an errand; False when one is already running."""
        if self._thread is not None:
            return False
        self._on_answer = on_answer
        self._on_failure = on_failure
        thread = QThread(self)
        worker = _ErrandWorker(errand)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.answered.connect(self._answered)
        worker.failed.connect(self._failed)
        self._thread = thread
        self._worker = worker
        thread.start()
        return True

    def wait(self) -> None:
        """Block until the running errand ends. For shutdown and for tests.

        A backup cannot be cancelled part way without leaving a partial zip to
        tidy, so it is waited for; on a fast disk that is a fraction of a
        second.
        """
        thread = self._thread
        if thread is not None:
            thread.quit()
            thread.wait()

    @Slot(object)
    def _answered(self, answer: object) -> None:
        """Tear the thread down, then hand the answer on."""
        callback = self._on_answer
        self._finish()
        callback(answer)

    @Slot(object)
    def _failed(self, error: Exception) -> None:
        """Tear the thread down, then hand the failure on."""
        callback = self._on_failure
        self._finish()
        callback(error)

    def _finish(self) -> None:
        """Stop the thread and release both it and the worker."""
        thread = self._thread
        self._thread = None
        self._worker = None
        if thread is not None:
            thread.quit()
            thread.wait()
            thread.deleteLater()


def _ignored(_value: object) -> None:
    """What an errand's answer goes to before anybody has asked for one."""
