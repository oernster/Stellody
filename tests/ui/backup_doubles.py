"""A window with the backup errands over an archive standing in. BACKUP.md."""

from __future__ import annotations

import threading
from datetime import UTC, datetime

from PySide6.QtWidgets import QApplication
from recording_player import RecordingPlayer
from tray_support import RememberingStore

from stellody.application.backing_up import BackupFailed, BackupRefused, Backups
from stellody.application.loading import LoadLibrary
from stellody.application.scan import ScanLibrary
from stellody.application.transport import Transport
from stellody.domain.backups import (
    BACKUP_FORMAT,
    Carried,
    Manifest,
    Refusal,
    RefusalKind,
    SchemaRange,
)
from stellody.ui.main_window import MainWindow

MOMENT = datetime(2026, 10, 12, 14, 5, tzinfo=UTC)
KNOWN = {"library.sqlite3": SchemaRange(0, 1)}
MANIFEST = Manifest(
    BACKUP_FORMAT, "1.0.0", MOMENT, (Carried("library.sqlite3", 1, "0" * 64),)
)


class HeldArchive:
    """An archive that can be held part way, can refuse and reports its thread."""

    def __init__(self) -> None:
        self.release = threading.Event()
        self.release.set()
        self.threads: list[int] = []
        self.fail = ""
        self.refuse = False
        self.staged: list[tuple[str, str]] = []

    def names_in(self, folder: str) -> frozenset[str]:
        return frozenset()

    def write(self, folder: str, name: str, moment: datetime) -> str:
        self.threads.append(threading.get_ident())
        self.release.wait()
        if self.fail:
            raise BackupFailed(self.fail)
        return f"{folder}/{name}"

    def read(self, backup: str) -> Manifest:
        self.release.wait()
        if self.refuse:
            raise BackupRefused(Refusal(RefusalKind.DAMAGED, "x.zip", detail="torn"))
        return MANIFEST

    def stage(self, backup: str, safety: str) -> None:
        self.staged.append((backup, safety))


def built(archive: HeldArchive | None, store: RememberingStore, left: list[int]):
    """A window over this archive and store, recording when it leaves."""

    def session():
        return ScanLibrary(None, None, None, store), store

    backups = (
        None
        if archive is None
        else Backups(archive, KNOWN, "app-backup", "app-before-restore", lambda: MOMENT)
    )
    return MainWindow(
        scan_session=session,
        loader=LoadLibrary(store),
        transport=Transport(RecordingPlayer()),
        settings=store,
        backups=backups,
        leave=lambda: left.append(1),
    )


def settled(window: MainWindow) -> None:
    """Let the running errand end and its answer reach the window."""
    window._errands.wait()
    QApplication.processEvents()


def file_menu_labels(window: MainWindow) -> list[str]:
    """The File menu's entries, in order, separators left out."""
    menu = window.menuBar().actions()[0].menu()
    return [action.text() for action in menu.actions() if not action.isSeparator()]
