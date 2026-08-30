"""The composition root: the one place that wires infrastructure to the UI.

This module sits above the layer boundaries on purpose. Nothing else in the
package is allowed to reach both sides.
"""

from __future__ import annotations

import sys
import traceback
from collections.abc import Callable

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from stellody.application.scan import LoadLibrary, ScanLibrary
from stellody.application.shapes import TrackShapes
from stellody.application.transport import Transport
from stellody.infrastructure import diary, instance, switch_reset
from stellody.infrastructure.audio import WasapiPlayback
from stellody.infrastructure.opening import open_store
from stellody.infrastructure.paths import (
    data_location,
    database_path,
    shape_cache_dir,
)
from stellody.infrastructure.probe import FlacProbe
from stellody.infrastructure.startup_log import clear, report_failure
from stellody.infrastructure.store import SqliteLibraryStore
from stellody.infrastructure.textfile import SidecarTextReader
from stellody.infrastructure.walker import FolderWalker
from stellody.infrastructure.waveform import FileWaveforms
from stellody.shared import resources
from stellody.shared.startup import starts_hidden
from stellody.shared.version import APP_AUTHOR, APP_NAME, __version__
from stellody.ui.close_prompt import CloseAction
from stellody.ui.main_window import MainWindow
from stellody.ui.settings_keys import (
    FALSE,
    SETTING_CLOSE,
    SETTING_REPEAT,
    SETTING_SHUFFLE,
)

# What a second launch returns once it has asked the running copy to show
# itself: it did what was wanted, so it is not a failure.
ALREADY_RUNNING = 0


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


def build_window(
    store: SqliteLibraryStore,
    leave: Callable[[], None] | None = None,
    note: Callable[[str], None] | None = None,
) -> MainWindow:
    """Assemble the window over a store, with real adapters behind every port."""
    return MainWindow(
        scan_session=scan_session(store.database),
        loader=LoadLibrary(store),
        transport=Transport(WasapiPlayback()),
        settings=store,
        shapes=TrackShapes(FileWaveforms(shape_cache_dir())),
        leave=leave,
        note=note,
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
    diary.note(f"launched with {arguments[1:]}")
    application = QApplication(arguments)
    configure(application)
    only = instance.SingleInstance()
    if not only.take():
        # Somebody asked for Stellody while it was already running, which
        # means the window they cannot see rather than a second copy of it.
        diary.note("another copy holds the claim, so asking it to come forward")
        answered = only.ask()
        diary.note(f"the ask was answered: {answered}; leaving")
        return ALREADY_RUNNING
    diary.note("took the claim, so this is the copy that runs")
    store, set_aside = open_store(database_path())
    if switch_reset.take(data_location()):
        for key in (SETTING_SHUFFLE, SETTING_REPEAT):
            store.set_setting(key, FALSE)
        # The remembered close choice is the same kind of thing: an answer
        # given once that outlives the install it was given to. A reinstall
        # that came back still acting on it would offer no way to notice.
        store.set_setting(SETTING_CLOSE, CloseAction.ASK.value)
    window = build_window(store, application.quit, diary.note)
    # Starting hidden is only honoured while there is a tray to restore from,
    # else the user would be left with nothing on screen at all.
    asked_to_hide = starts_hidden(arguments)
    diary.note(f"asked to start hidden: {asked_to_hide}; tray: {window.tray_active}")
    if not (asked_to_hide and window.tray_active):
        diary.note("showing the window because this launch was not a quiet one")
        window.show()
    else:
        diary.note("staying in the tray, as this launch asked")
    # Launch reads the store and nothing else. Scanning on startup reached for
    # the music folder every time the application opened, which on a large
    # library is felt; nobody asked for it by starting the application.
    window.load_remembered()
    if set_aside is not None:
        window.report_library_set_aside(set_aside)
    listening = only.listen(window.restore_for_channel)
    diary.note(f"listening on the activation channel: {listening}")
    code = application.exec()
    diary.note(f"the event loop ended with {code}")
    store.close()
    diary.note("store closed")
    only.release()
    diary.note(f"claim released; leaving with {code}")
    return code
