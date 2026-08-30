"""Looking a cover up without making the window wait.

A search reaches two services and waits its turn between requests, because the
terms ask for no more than one a second. Measured on 2026-08-30, one album came
back with 19 pictures across 8 releases in 13.5 seconds. That is far too long
to spend on the interface thread, so the looking up runs on a thread of its own
and the chooser fills in as answers arrive rather than after the last of them.

Two errands rather than one. A search offers the candidates first, then fetches
a thumbnail for each, so a tile is drawn the moment its own picture lands.
Keeping a chosen picture is the second errand: it fetches the full size image,
which is one more wait nobody should watch the window freeze through.

**What cancelling can and cannot do.** The flag is read between requests, so a
search stops at the next boundary rather than in the middle of one. A request
already in flight runs to its own timeout and its answer is then dropped rather
than drawn.

**Dropping it is the worker's own job, twice over.** It is checked after every
slow call and before the emit that follows, so a cancelled errand says nothing;
letting go of one also disconnects it, so anything it did say reaches nobody.
The runner cannot do this by asking who sent an answer: measured here, a queued
cross thread signal arrives with no sender at all, so a check reading `None`
against a runner that has just dropped its worker passes exactly when it should
fail. The test for it is `test_the_answer_to_a_search_let_go_of_is_dropped`,
which failed on that check before it was written this way.

A thread that has not finished by the time it is let go is held rather than
forgotten, since Qt ends the process over a running thread that is destroyed.
"""

from __future__ import annotations

from PySide6.QtCore import QObject, QThread, Signal, Slot

from stellody.application.choosing_covers import ChooseCover
from stellody.domain.cover_choice import CoverCandidate
from stellody.domain.identity import AlbumIdentity

# Long enough for a request between boundaries to finish, short enough that
# closing the chooser never feels like a hang. A search is pure reading, so
# abandoning one costs nothing but the reading already done.
WAIT_MS = 2000


class SearchWorker(QObject):
    """One album's search, run on a thread that is not the interface's."""

    offered = Signal(object)
    previewed = Signal(int, object)
    done = Signal()

    def __init__(self, chooser: ChooseCover, identity: AlbumIdentity) -> None:
        super().__init__()
        self._chooser = chooser
        self._identity = identity
        self._cancelled = False

    def cancel(self) -> None:
        """Ask the search to stop at the next request boundary, saying nothing."""
        self._cancelled = True

    def release(self) -> None:
        """Drop every connection, so a late answer reaches nobody at all."""
        self.offered.disconnect()
        self.previewed.disconnect()
        self.done.disconnect()

    @Slot()
    def run(self) -> None:
        """Offer what came back, then a thumbnail at a time.

        Cancellation is read after each slow call and before the emit that
        would follow it, so an errand nobody waits for finishes quietly rather
        than drawing into a chooser that has closed.

        Nothing here may raise. It runs on a thread with nobody above it to
        catch anything; a picture that cannot be had is not a reason to take
        the application down.
        """
        candidates = self._searched()
        if self._cancelled:
            return
        self.offered.emit(candidates)
        for position, candidate in enumerate(candidates):
            if self._cancelled:
                return
            picture = self._preview(candidate)
            if self._cancelled:
                return
            self.previewed.emit(position, picture)
        self.done.emit()

    def _searched(self) -> tuple[CoverCandidate, ...]:
        """What is on offer; nothing when the search could not be made."""
        try:
            return self._chooser.offer(self._identity)
        except Exception:  # noqa: BLE001 - a search must not end the run
            return ()

    def _preview(self, candidate: CoverCandidate) -> bytes | None:
        """One thumbnail; None when it could not be had."""
        try:
            return self._chooser.preview(candidate)
        except Exception:  # noqa: BLE001 - a picture must not end the run
            return None


class KeepWorker(QObject):
    """The chosen picture, fetched and kept off the interface thread."""

    kept = Signal(str, object)

    def __init__(self, chooser: ChooseCover, key: str, candidate: CoverCandidate):
        super().__init__()
        self._chooser = chooser
        self._key = key
        self._candidate = candidate
        self._cancelled = False

    def cancel(self) -> None:
        """Say nothing when this finishes.

        The fetch itself cannot be stopped: it is already the only thing this
        thread does. What cancelling means here is that the answer is not
        announced, which is the same promise the search makes.
        """
        self._cancelled = True

    def release(self) -> None:
        """Drop every connection, so a late answer reaches nobody at all."""
        self.kept.disconnect()

    @Slot()
    def run(self) -> None:
        """Fetch the picture and keep it, then say what was kept.

        None means the album is exactly as it was: a fetch that fails keeps
        nothing, so there is nothing to undo.
        """
        try:
            kept = self._chooser.accept(self._key, self._candidate)
        except Exception:  # noqa: BLE001 - a picture must not end the run
            kept = None
        if not self._cancelled:
            self.kept.emit(self._key, kept)


class CoverRunner(QObject):
    """Keeps one errand in flight and drops the answer to any it let go of."""

    offered = Signal(object)
    previewed = Signal(int, object)
    searched = Signal()
    kept = Signal(str, object)

    def __init__(self, chooser: ChooseCover, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._chooser = chooser
        self._thread: QThread | None = None
        self._worker: SearchWorker | KeepWorker | None = None
        self._retired: list[QThread] = []

    @property
    def running(self) -> bool:
        """True while an errand is in flight."""
        return self._thread is not None

    @property
    def retired(self) -> int:
        """How many threads were let go of while still in a request."""
        return len(self._retired)

    def search(self, identity: AlbumIdentity) -> None:
        """Look this album up, dropping whatever was being looked up."""
        worker = SearchWorker(self._chooser, identity)
        # Connected to bound methods of this object, which lives on the
        # interface thread, so an answer crosses back rather than arriving on
        # the searching thread and being drawn from it.
        worker.offered.connect(self._on_offered)
        worker.previewed.connect(self._on_previewed)
        worker.done.connect(self._on_done)
        self._begin(worker)

    def keep(self, key: str, candidate: CoverCandidate) -> None:
        """Fetch and keep this picture, ending the search that offered it."""
        worker = KeepWorker(self._chooser, key, candidate)
        worker.kept.connect(self._on_kept)
        self._begin(worker)

    def cancel(self) -> None:
        """Let go of the errand in flight. Harmless when there is none."""
        worker, thread = self._worker, self._thread
        self._worker = None
        self._thread = None
        if worker is not None:
            worker.cancel()
            worker.release()
        if thread is not None and not self._let_go(thread):
            self._retired.append(thread)

    def stop(self) -> None:
        """Let go of everything on the way out."""
        self.cancel()
        self._retired = [thread for thread in self._retired if not self._let_go(thread)]

    def _begin(self, worker: SearchWorker | KeepWorker) -> None:
        """Put one errand on a thread of its own, after dropping the last."""
        self.cancel()
        thread = QThread(self)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        self._thread = thread
        self._worker = worker
        thread.start()

    def _let_go(self, thread: QThread) -> bool:
        """Ask a thread to end; True when it did within the wait."""
        thread.quit()
        return thread.wait(WAIT_MS)

    @Slot(object)
    def _on_offered(self, candidates: object) -> None:
        """Pass on what a search offered."""
        self.offered.emit(candidates)

    @Slot(int, object)
    def _on_previewed(self, position: int, thumbnail: object) -> None:
        """Pass on one thumbnail, by the place in the offer it belongs to."""
        self.previewed.emit(position, thumbnail)

    @Slot()
    def _on_done(self) -> None:
        """Say the search has finished, so a wait can stop being drawn."""
        self._finished()
        self.searched.emit()

    @Slot(str, object)
    def _on_kept(self, key: str, kept: object) -> None:
        """Pass on the picture that was kept, else the news that none was."""
        self._finished()
        self.kept.emit(key, kept)

    def _finished(self) -> None:
        """Release the thread of an errand that ran to its own end.

        Held apart from `cancel` because there is nothing here to stop and
        nothing to drop: the answer has already been given. Without this a
        window sitting idle keeps a thread for every album ever looked up and
        the runner reports itself busy for the rest of the session.
        """
        thread = self._thread
        self._worker = None
        self._thread = None
        if thread is not None:
            self._let_go(thread)
