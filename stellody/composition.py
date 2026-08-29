"""The composition root: the one place that wires infrastructure to the UI.

This module sits above the layer boundaries on purpose. Nothing else in the
package is allowed to reach both sides.
"""

from __future__ import annotations

import sys
import traceback

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from stellody.application.scan import LoadLibrary, ScanLibrary
from stellody.application.transport import Transport
from stellody.infrastructure.audio import WasapiPlayback
from stellody.infrastructure.paths import database_path
from stellody.infrastructure.probe import FlacProbe
from stellody.infrastructure.startup_log import clear, report_failure
from stellody.infrastructure.store import SqliteLibraryStore
from stellody.infrastructure.textfile import SidecarTextReader
from stellody.infrastructure.walker import FolderWalker
from stellody.shared import resources
from stellody.shared.startup import starts_hidden
from stellody.shared.version import APP_AUTHOR, APP_NAME, __version__
from stellody.ui.main_window import MainWindow


def scan_session(database: str):
    """Open a scanner and its own store, on whichever thread asks for one.

    SQLite refuses a connection used from a thread other than the one that
    made it, so the scan cannot borrow the window's. It opens its own against
    the same file and hands it back to be closed when the scan ends.
    """

    def open_session() -> tuple[ScanLibrary, SqliteLibraryStore]:
        store = SqliteLibraryStore(database)
        scanner = ScanLibrary(FolderWalker(), FlacProbe(), SidecarTextReader(), store)
        return scanner, store

    return open_session


def build_window(store: SqliteLibraryStore) -> MainWindow:
    """Assemble the window over a store, with real adapters behind every port."""
    return MainWindow(
        scan_session=scan_session(store.database),
        loader=LoadLibrary(store),
        transport=Transport(WasapiPlayback()),
        settings=store,
    )


def configure(application: QApplication) -> None:
    """Give the application its identity and icon."""
    application.setApplicationName(APP_NAME)
    application.setApplicationDisplayName(APP_NAME)
    application.setApplicationVersion(__version__)
    application.setOrganizationName(APP_AUTHOR)
    application.setQuitOnLastWindowClosed(False)
    icon_path = resources.application_icon_path() or resources.window_icon_path()
    if icon_path is not None:
        application.setWindowIcon(QIcon(str(icon_path)))


def main(argv: list[str] | None = None) -> int:
    """Start Stellody, in the tray when the sign-in entry asked for that."""
    clear()
    try:
        return _start(argv)
    except Exception:
        report_failure(traceback.format_exc())
        raise


def _start(argv: list[str] | None = None) -> int:
    """Everything main does, with the reporting wrapped around it."""
    arguments = list(sys.argv if argv is None else argv)
    application = QApplication(arguments)
    configure(application)
    store = SqliteLibraryStore(str(database_path()))
    window = build_window(store)
    # Starting hidden is only honoured while there is a tray to restore from,
    # else the user would be left with nothing on screen at all.
    if not (starts_hidden(arguments) and window.tray_active):
        window.show()
    # Launch reads the store and nothing else. Scanning on startup reached for
    # the music folder every time the application opened, which on a large
    # library is felt; nobody asked for it by starting the application.
    window.load_remembered()
    code = application.exec()
    store.close()
    return code
