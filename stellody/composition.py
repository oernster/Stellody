"""The composition root: the one place that wires infrastructure to the UI.

This module sits above the layer boundaries on purpose. Nothing else in the
package is allowed to reach both sides.
"""

from __future__ import annotations

import sys

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from stellody.application.scan import ScanLibrary
from stellody.infrastructure.paths import database_path
from stellody.infrastructure.probe import FlacProbe
from stellody.infrastructure.store import SqliteLibraryStore
from stellody.infrastructure.textfile import SidecarTextReader
from stellody.infrastructure.walker import FolderWalker
from stellody.shared import resources
from stellody.shared.version import APP_AUTHOR, APP_NAME, __version__
from stellody.ui.main_window import MainWindow


def build_window(store: SqliteLibraryStore) -> MainWindow:
    """Assemble the window over a store, with real adapters behind every port."""
    scanner = ScanLibrary(FolderWalker(), FlacProbe(), SidecarTextReader(), store)
    return MainWindow(scanner=scanner, settings=store)


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


def main() -> int:
    """Start Stellody."""
    application = QApplication(sys.argv)
    configure(application)
    store = SqliteLibraryStore(str(database_path()))
    window = build_window(store)
    window.show()
    if window.library_root:
        window.start_scan()
    code = application.exec()
    store.close()
    return code
