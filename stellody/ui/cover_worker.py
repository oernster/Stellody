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
**What holds it has to outlive the errand.** It was held by the runner, which
belongs to the chooser dialog, so cancelling a search and closing the dialog
destroyed the very thing keeping the thread alive: measured on 2026-09-05, that
is exactly the abort Oliver met, `QThread: Destroyed while thread is still
running` with Qt6Core ending the process. A `ThreadKeeper` given by the window
outlives every dialog it opens, so a straggler is held by something that is
still there when it finishes.
"""

from __future__ import annotations

from PySide6.QtCore import QObject, QThread, Signal, Slot

from stellody.application.choosing_covers import ChooseCover
from stellody.domain.cover_choice import CoverCandidate, CoverOffer
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
        offer = self._searched()
        if self._cancelled:
            return
        self.offered.emit(offer)
        for position, candidate in enumerate(offer.candidates):
            if self._cancelled:
                return
            picture = self._preview(candidate)
            if self._cancelled:
                return
            self.previewed.emit(position, picture)
        self.done.emit()

    def _searched(self) -> CoverOffer:
        """What is on offer; nothing when the search could not be made."""
        try:
            return self._chooser.offer(self._identity)
        except Exception:  # noqa: BLE001 - a search must not end the run
            return CoverOffer()

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


class ThreadKeeper(QObject):
    """Holds threads that outlived the errands that started them.

    Given to a runner by something long lived, the window, so that a thread
    still in a request when its dialog closes is owned by an object that is
    still there. Each is let go of the moment it finishes, so nothing is held
    a second longer than the request it is waiting on.
    """

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._held: list[tuple[QThread, QObject]] = []

    @property
    def waiting(self) -> int:
        """How many threads are still in a request nobody is waiting for."""
        return len(self._held)

    def hold(self, thread: QThread, worker: QObject) -> None:
        """Take a thread over, with the worker whose run it is still in.

        The worker is held too. It sits on that thread with no parent of its
        own, so dropping the last reference to it would delete an object that
        is in the middle of its own method.

        Connected before the finished state is read, then read: a thread that
        ends between the two would otherwise be held for ever, since its one
        announcement had already been made when the connection was set up.
        """
        thread.setParent(self)
        self._held.append((thread, worker))
        thread.finished.connect(lambda: self._forget(thread))
        if thread.isFinished():
            self._forget(thread)

    def stop(self) -> None:
        """Ask everything held to end, then let go of whatever did."""
        for thread, _worker in list(self._held):
            thread.quit()
            if thread.wait(WAIT_MS):
                self._forget(thread)

    def _forget(self, thread: QThread) -> None:
        """Drop one thread that has finished, plus the worker it carried.

        Asked twice for the same thread where it ended as it was handed over,
        so it removes what is there rather than assuming anything is.
        """
        held = [pair for pair in self._held if pair[0] is not thread]
        if len(held) == len(self._held):
            return
        self._held = held
        thread.deleteLater()


class CoverRunner(QObject):
    """Keeps one errand in flight and drops the answer to any it let go of."""

    offered = Signal(object)
    previewed = Signal(int, object)
    searched = Signal()
    kept = Signal(str, object)

    def __init__(
        self,
        chooser: ChooseCover,
        parent: QObject | None = None,
        keeper: ThreadKeeper | None = None,
    ) -> None:
        super().__init__(parent)
        self._chooser = chooser
        self._thread: QThread | None = None
        self._worker: SearchWorker | KeepWorker | None = None
        # Given one by the window, which outlives every chooser it opens. A
        # runner left to keep its own is only safe while it outlives its own
        # errands, which is true of a runner in a test and false of one in a
        # dialog that can be closed mid search.
        self._keeper = keeper or ThreadKeeper(self)

    @property
    def running(self) -> bool:
        """True while an errand is in flight."""
        return self._thread is not None

    @property
    def retired(self) -> int:
        """How many threads were let go of while still in a request."""
        return self._keeper.waiting

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
        if thread is not None and worker is not None:
            # Handed over rather than waited for. A worker inside a request
            # cannot answer a quit until that request ends, so waiting here
            # froze the window for the whole wait every time somebody
            # cancelled: measured at two seconds, on the very gesture that
            # was asking for something to stop happening.
            thread.quit()
            self._keeper.hold(thread, worker)

    def stop(self) -> None:
        """Let go of everything on the way out."""
        self.cancel()
        self._keeper.stop()

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
