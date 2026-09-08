"""Asking what one candidate artist released, off the interface thread.

One expansion is one paced request, so it costs at least the gap the terms
ask for: a second and a tenth before the question even leaves. That is far
too long to spend on the thread that draws the window, which is why this
exists rather than the dialog simply calling the use case.

The same shape as `discovery_worker.py` beside it and for the same reasons:
every answer crosses back as a Qt signal whose receiver is a bound method of
a QObject living on the interface thread. A signal connected to a bare
callable runs in the SENDER's thread instead, which is how a background
thread comes to touch a widget.

**One question at a time per artist, several artists at once.** Somebody
opening three candidates in a row should not wait for the first before the
second is even asked; two questions about the SAME artist are the same
question, so the second is refused rather than queued. The gap owed to the
catalogue is kept by the gate the requests share, not by this.
"""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QObject, QThread, Signal, Slot

from stellody.application.expanding import Expansion
from stellody.ui.results_words import plainly
from stellody.ui.standing_in import say_nothing

# Handed one line about a failure, for the log rather than for the screen.
Note = Callable[[str], None]

# Long enough for a request already in flight to notice it is unwanted, short
# enough that a dialog closing cannot hold the window up. The same reasoning
# as the discovery runner's own wait, which is the longer of the two jobs.
WAIT_MS = 30000


class ExpansionWorker(QObject):
    """Asks about one artist and says what came back."""

    ready = Signal(str, object)
    failed = Signal(str, str)

    def __init__(
        self,
        expansion: Expansion,
        identifier: str,
        note: Note = say_nothing,
    ) -> None:
        super().__init__()
        self._expansion = expansion
        self._identifier = identifier
        self._note = note
        self._cancelled = False

    def cancel(self) -> None:
        """Give up on the question, whether or not it has been asked yet."""
        self._cancelled = True

    @Slot()
    def run(self) -> None:
        """Ask, then report the answer or what went wrong asking.

        Every failure is reported rather than only the ones anticipated. An
        artist whose lookup died in silence would sit open and empty for ever,
        saying nothing about why. FR-D32.
        """
        try:
            releases = self._expansion.releases_of(
                self._identifier, lambda: self._cancelled
            )
        except Exception as error:  # noqa: BLE001 - reported, never swallowed
            # The machine's account goes to the log and the person's account
            # goes on the row. Both halves are kept: one of them is unreadable
            # to whoever is using this, the other is useless to whoever is
            # fixing it.
            self._note(
                f"expanding {self._identifier} failed: "
                f"{type(error).__name__}: {error}"
            )
            self.failed.emit(self._identifier, plainly(error))
            return
        self.ready.emit(self._identifier, releases)


class ExpansionRunner(QObject):
    """Owns the threads the questions are asked on and tidies them away."""

    ready = Signal(str, object)
    failed = Signal(str, str)

    def __init__(
        self,
        expansion: Expansion,
        parent: QObject | None = None,
        note: Note = say_nothing,
    ) -> None:
        super().__init__(parent)
        self._expansion = expansion
        self._note = note
        self._asking: dict[str, tuple[QThread, ExpansionWorker]] = {}

    def asking_about(self, identifier: str) -> bool:
        """True while a question about this artist is in flight."""
        return identifier in self._asking

    def ask(self, identifier: str) -> bool:
        """Ask about this artist; False where the same question is in flight."""
        if identifier in self._asking:
            return False
        thread = QThread(self)
        worker = ExpansionWorker(self._expansion, identifier, self._note)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.ready.connect(self._on_ready)
        worker.failed.connect(self._on_failed)
        self._asking[identifier] = (thread, worker)
        thread.start()
        return True

    def stop(self, milliseconds: int = WAIT_MS) -> None:
        """Give up on every question and wait for the threads to end.

        Waited for rather than abandoned, unlike a run: a question is one
        request rather than eleven minutes of them; it is called as the dialog
        closes, which is exactly when a thread Qt is about to tear down must
        not still be running.
        """
        for thread, worker in tuple(self._asking.values()):
            worker.cancel()
            thread.quit()
            thread.wait(milliseconds)
        self._asking.clear()

    @Slot(str, object)
    def _on_ready(self, identifier: str, releases: object) -> None:
        """Relay an answer on the interface thread, then let the thread go."""
        self._done_with(identifier)
        self.ready.emit(identifier, releases)

    @Slot(str, str)
    def _on_failed(self, identifier: str, reason: str) -> None:
        """Relay a failure on the interface thread, then let the thread go."""
        self._done_with(identifier)
        self.failed.emit(identifier, reason)

    def _done_with(self, identifier: str) -> None:
        """Stop the thread this question was asked on and release it."""
        held = self._asking.pop(identifier, None)
        if held is None:
            return
        thread, _worker = held
        thread.quit()
        thread.wait()
        thread.deleteLater()
