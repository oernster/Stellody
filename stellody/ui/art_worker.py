"""Reading album covers without making the window wait.

A cover is read from disk and decoded, which is far too slow to do while a
library is being drawn: a library of a few hundred albums would stutter on
every scroll. So covers are read on a thread of its own and arrive when they
arrive; until then an album draws its placeholder.

One cover is read at a time rather than many at once. The work is disk bound,
so several threads would queue on the same drive while costing the ordering
that makes a visible album arrive before one nobody has scrolled to yet.

An album is asked for once. An album with no cover anywhere answers None;
that answer is kept exactly as a picture is, so scrolling past it again does
not send anybody back to the disk to be told the same thing.
"""

from __future__ import annotations

from collections import deque

from PySide6.QtCore import QObject, QThread, Signal, Slot

from stellody.application.artwork import AlbumArt, AlbumArtSources

# Long enough for a read in flight to finish, short enough that shutting down
# never feels like a hang. Reading a cover is pure reading, so abandoning one
# costs nothing but the reading already done.
WAIT_MS = 2000


class ArtWorker(QObject):
    """One cover, read on a thread that is not the interface's."""

    read = Signal(str, object)

    def __init__(self, art: AlbumArt, sources: AlbumArtSources) -> None:
        super().__init__()
        self._art = art
        self._sources = sources

    @Slot()
    def run(self) -> None:
        """Read one album's cover, then say so. None when there is none.

        Nothing here may raise. It runs on a thread with nobody above it to
        catch anything; a cover that cannot be drawn is not a reason to take
        the application down.
        """
        try:
            cover = self._art.reading(self._sources)
        except Exception:  # noqa: BLE001 - a picture must not end the run
            cover = None
        self.read.emit(self._sources.key, cover)


class ArtRunner(QObject):
    """Reads the albums that have been asked for, one after another.

    A thread lives only as long as the cover it is reading, so a window
    sitting idle holds none. That matters more here than it looks: a reader
    kept alive between covers is a running thread at the moment the window is
    destroyed, which Qt ends the process over.
    """

    ready = Signal(str, object)

    def __init__(self, art: AlbumArt, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._art = art
        self._queue: deque[AlbumArtSources] = deque()
        self._asked: set[str] = set()
        self._thread: QThread | None = None
        self._worker: ArtWorker | None = None

    @property
    def running(self) -> bool:
        """True while a cover is being read."""
        return self._thread is not None

    @property
    def pending(self) -> int:
        """How many albums are still waiting to be read."""
        return len(self._queue)

    def want(self, sources: AlbumArtSources) -> None:
        """Ask for an album's cover, unless it has been asked for already."""
        if sources.key in self._asked:
            return
        self._asked.add(sources.key)
        self._queue.append(sources)
        self._pump()

    def forget(self) -> None:
        """Drop what has been asked, for a library that has been rescanned."""
        self._queue.clear()
        self._asked.clear()

    def wait(self, milliseconds: int = WAIT_MS) -> None:
        """Block until the read in flight finishes. For shutdown and for tests."""
        self._let_go(milliseconds)

    def stop(self) -> None:
        """Let go of everything. Harmless when nothing is running."""
        self.forget()
        self._let_go(WAIT_MS)

    def _let_go(self, milliseconds: int) -> None:
        """Release the thread in flight, if there is one."""
        thread = self._thread
        self._thread = None
        self._worker = None
        if thread is not None:
            thread.quit()
            thread.wait(milliseconds)

    def _pump(self) -> None:
        """Start the next cover, when nothing else is being read."""
        if self._thread is not None or not self._queue:
            return
        thread = QThread(self)
        worker = ArtWorker(self._art, self._queue.popleft())
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        # Connected to a bound method of this object, which lives on the
        # interface thread, so the answer crosses back rather than arriving
        # on the reading thread and being drawn from it.
        worker.read.connect(self._on_read)
        self._thread = thread
        self._worker = worker
        thread.start()

    @Slot(str, object)
    def _on_read(self, key: str, cover: object) -> None:
        """Pass a cover on, then start the next one."""
        self._let_go(WAIT_MS)
        self.ready.emit(key, cover)
        self._pump()
