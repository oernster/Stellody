"""The composition root: the one place that wires infrastructure to the UI.

This module sits above the layer boundaries on purpose. Nothing else in the
package is allowed to reach both sides.
"""

from __future__ import annotations

import sys
import traceback

from PySide6.QtCore import QTimer
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from stellody.application.scan import LoadLibrary, ScanLibrary
from stellody.application.transport import Transport
from stellody.infrastructure import instance, switch_reset
from stellody.infrastructure.audio import WasapiPlayback
from stellody.infrastructure.opening import open_store
from stellody.infrastructure.paths import data_location, database_path
from stellody.infrastructure.probe import FlacProbe
from stellody.infrastructure.startup_log import clear, report_failure
from stellody.infrastructure.store import SqliteLibraryStore
from stellody.infrastructure.textfile import SidecarTextReader
from stellody.infrastructure.walker import FolderWalker
from stellody.shared import resources
from stellody.shared.startup import starts_hidden
from stellody.shared.version import APP_AUTHOR, APP_NAME, __version__
from stellody.ui.main_window import MainWindow
from stellody.ui.settings_keys import FALSE, SETTING_REPEAT, SETTING_SHUFFLE

# What a second launch returns once it has asked the running copy to show
# itself: it did what was wanted, so it is not a failure.
ALREADY_RUNNING = 0
# Often enough that a click feels answered, rarely enough to cost nothing.
ATTENTION_POLL_MS = 400


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
    claim = instance.Claim()
    if not claim.take():
        # Somebody asked for Stellody while it was already running, which
        # means the window they cannot see rather than a second copy of it.
        instance.ask(data_location())
        return ALREADY_RUNNING
    store, set_aside = open_store(database_path())
    if switch_reset.take(data_location()):
        for key in (SETTING_SHUFFLE, SETTING_REPEAT):
            store.set_setting(key, FALSE)
    window = build_window(store)
    # Starting hidden is only honoured while there is a tray to restore from,
    # else the user would be left with nothing on screen at all.
    if not (starts_hidden(arguments) and window.tray_active):
        window.show()
    # Launch reads the store and nothing else. Scanning on startup reached for
    # the music folder every time the application opened, which on a large
    # library is felt; nobody asked for it by starting the application.
    window.load_remembered()
    if set_aside is not None:
        window.report_library_set_aside(set_aside)
    watch = QTimer(window)
    watch.timeout.connect(lambda: _come_forward(window))
    watch.start(ATTENTION_POLL_MS)
    code = application.exec()
    store.close()
    claim.release()
    return code


def _come_forward(window: MainWindow) -> None:
    """Show the window when another launch asked for it."""
    if instance.asked(data_location()):
        window.restore_from_tray()
