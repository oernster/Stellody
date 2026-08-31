"""The scan runs on its own thread, so it must open its own store there.

Measured, not theorised: SQLite refuses a connection used from a thread other
than the one that created it, so a scanner built on the interface thread raised
`sqlite3.ProgrammingError` on its first statement. The worker caught only
OSError, so the thread ended in silence: no progress, no report, no failure. The
bar span on and the status line went on saying it was scanning, for ever.

Two invariants hold that shut: the session is opened ON the scanning thread;
every failure is reported rather than swallowed.
"""

from __future__ import annotations

import time

from PySide6.QtCore import QThread
from PySide6.QtWidgets import QApplication

from stellody.application.scan import ScanLibrary
from stellody.application.values import FolderListing
from stellody.infrastructure.probe import FlacProbe
from stellody.infrastructure.store import SqliteLibraryStore
from stellody.infrastructure.textfile import SidecarTextReader
from stellody.infrastructure.walker import FolderWalker
from stellody.ui.worker import ScanRunner

ROOT = "H:/FLACMusic"
PATIENCE_S = 5.0
POLL_S = 0.005


class EmptyWalker:
    """A library with one folder and nothing in it."""

    def count(self, root: str) -> int:
        """One folder."""
        return 1

    def walk(self, root: str):
        """That one folder, holding no audio."""
        yield FolderListing(folder=f"{root}/Album", audio=())


class QuietStore:
    """A store that answers everything and remembers being closed."""

    def __init__(self) -> None:
        self.closed = False

    def file_signatures(self) -> dict:
        """Nothing on record."""
        return {}

    def load_folders(self) -> tuple:
        """Nothing on record."""
        return ()

    def save_folder(self, record) -> None:
        """Accept the record."""

    def mark_absent(self, seen_paths) -> int:
        """Nothing went missing."""
        return 0

    def close(self) -> None:
        """Record that the handle was given back."""
        self.closed = True


def drain(runner: ScanRunner, application: QApplication) -> None:
    """Let the scan finish, without waiting on it for ever."""
    deadline = time.monotonic() + PATIENCE_S
    while runner.running and time.monotonic() < deadline:
        application.processEvents()
        time.sleep(POLL_S)
    application.processEvents()


def test_the_store_is_opened_on_the_thread_that_scans(
    application: QApplication,
) -> None:
    """A connection made on the interface thread is refused by SQLite."""
    interface_thread = QThread.currentThread()
    opened_on: list[QThread] = []
    store = QuietStore()

    def session():
        opened_on.append(QThread.currentThread())
        return ScanLibrary(EmptyWalker(), None, None, store), store

    runner = ScanRunner()
    reports: list[object] = []
    runner.completed.connect(reports.append)
    assert runner.start(session, ROOT) is True
    drain(runner, application)
    assert len(opened_on) == 1
    assert opened_on[0] is not interface_thread
    assert reports, "the scan must report back"
    assert store.closed is True


def test_a_session_that_cannot_be_opened_is_reported_not_swallowed(
    application: QApplication,
) -> None:
    """This exact failure ran silently: the scan looked like it never ended."""

    def session():
        raise RuntimeError("SQLite objects created in a thread")

    runner = ScanRunner()
    failures: list[str] = []
    runner.failed.connect(failures.append)
    assert runner.start(session, ROOT) is True
    drain(runner, application)
    assert failures == ["SQLite objects created in a thread"]


def test_a_scan_that_raises_part_way_is_reported_too(
    application: QApplication,
) -> None:
    class ExplodingWalker:
        """A walk that fails once it is under way."""

        def count(self, root: str) -> int:
            """One folder, it claims."""
            return 1

        def walk(self, root: str):
            """Fail rather than yield."""
            raise ValueError("the drive went away")
            yield  # pragma: no cover - unreachable, kept so this is a generator

    store = QuietStore()
    runner = ScanRunner()
    failures: list[str] = []
    runner.failed.connect(failures.append)
    runner.start(
        lambda: (ScanLibrary(ExplodingWalker(), None, None, store), store), ROOT
    )
    drain(runner, application)
    assert failures == ["the drive went away"]
    assert store.closed is True


def test_a_real_store_survives_being_scanned_from_another_thread(
    application: QApplication, tmp_path
) -> None:
    """The end to end shape of the failure: real SQLite, real thread, real walk."""
    library = tmp_path / "library"
    (library / "Artist" / "Album").mkdir(parents=True)
    (library / "Artist" / "Album" / "01.flac").write_bytes(b"not really flac")
    database = str(tmp_path / "library.sqlite3")
    interface_store = SqliteLibraryStore(database)

    def session():
        store = SqliteLibraryStore(database)
        return (
            ScanLibrary(FolderWalker(), FlacProbe(), SidecarTextReader(), store),
            store,
        )

    runner = ScanRunner()
    reports: list[object] = []
    failures: list[str] = []
    runner.completed.connect(reports.append)
    runner.failed.connect(failures.append)
    runner.start(session, str(library))
    drain(runner, application)
    assert failures == []
    assert len(reports) == 1
    interface_store.close()
