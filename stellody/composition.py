"""The composition root: the one place that wires infrastructure to the UI.

This module sits above the layer boundaries on purpose. Nothing else in the
package is allowed to reach both sides.
"""

from __future__ import annotations

import os
import sys
import traceback
from collections.abc import Callable

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from stellody.application.artwork import AlbumArt
from stellody.application.choosing_covers import ChooseCover
from stellody.application.editing import TagEditing
from stellody.application.listening import ListeningLog
from stellody.application.pictures import Pictures
from stellody.application.repairs import Repairs
from stellody.application.scan import LoadLibrary, ScanLibrary
from stellody.application.shapes import TrackShapes
from stellody.application.transport import Transport
from stellody.application.updates import UpdateService, platform_key_for
from stellody.infrastructure import diary, instance, switch_reset
from stellody.infrastructure.artwork import FileArtwork
from stellody.infrastructure.audio import WasapiPlayback
from stellody.infrastructure.cover_search import ArchiveCovers
from stellody.infrastructure.covers import EmbeddedPictures
from stellody.infrastructure.opening import open_store
from stellody.infrastructure.paths import (
    art_cache_dir,
    data_location,
    database_path,
    shape_cache_dir,
)
from stellody.infrastructure.probe import AudioProbe
from stellody.infrastructure.startup_log import clear, report_failure
from stellody.infrastructure.store import SqliteLibraryStore
from stellody.infrastructure.textfile import SidecarTextReader
from stellody.infrastructure.update_source import GitHubReleases
from stellody.infrastructure.video import VideoReader
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
from stellody.ui.tips import show_tips_quickly

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
        scanner = ScanLibrary(FolderWalker(), AudioProbe(), SidecarTextReader(), store)
        return scanner, store

    return open_session


def build_window(
    store: SqliteLibraryStore,
    leave: Callable[[], None] | None = None,
    note: Callable[[str], None] | None = None,
) -> MainWindow:
    """Assemble the window over a store, with real adapters behind every port.

    One artwork store rather than two. Reading a cover and keeping a chosen one
    are separate services over the same directory, so a picture chosen from the
    archive is found by the reader afterwards instead of sitting in a second
    cache nothing consults.

    This is the only module that may name the search client or the update
    source, which are the only two things in Stellody that can open a
    connection; a structural test says so rather than a comment.
    """
    artwork = FileArtwork(art_cache_dir(), EmbeddedPictures())
    listening = ListeningLog(store)
    listening.load()
    return MainWindow(
        scan_session=scan_session(store.database),
        loader=LoadLibrary(store),
        transport=Transport(WasapiPlayback()),
        settings=store,
        shapes=TrackShapes(FileWaveforms(shape_cache_dir())),
        listening=listening,
        art=AlbumArt(artwork),
        chooser=ChooseCover(ArchiveCovers(), artwork),
        repairs=Repairs(store),
        tag_editing=TagEditing(store),
        pictures=Pictures(VideoReader),
        updates=UpdateService(
            GitHubReleases(), __version__, platform_key_for(sys.platform)
        ),
        leave=leave,
        note=note,
    )


def configure(application: QApplication) -> None:
    """Give the application its identity, its icon and its quick tooltips."""
    show_tips_quickly(application)
    application.setApplicationName(APP_NAME)
    application.setApplicationDisplayName(APP_NAME)
    application.setApplicationVersion(__version__)
    application.setOrganizationName(APP_AUTHOR)
    application.setQuitOnLastWindowClosed(False)
    icon_path = resources.application_icon_path() or resources.window_icon_path()
    if icon_path is not None:
        application.setWindowIcon(QIcon(str(icon_path)))


def leave_at_once(code: int) -> None:
    """End the process where unwinding would end it worse.

    A cover lookup cannot be stopped in the middle of a network read: the
    request runs to its own timeout, which is twenty seconds for a search and
    thirty for a picture. Quitting inside one leaves a thread running that Qt
    then destroys as it tears the application down; Qt ends the process over
    that with an abort rather than an exit: measured on 2026-09-05,
    `QThread: Destroyed while thread is still running` from Qt6Core.

    So the process is left before the tearing down begins. Everything that
    outlives a run has already been put away by the time this is reached: the
    store is closed and the single-instance claim released. What is skipped is
    the destruction of objects the operating system is about to reclaim
    anyway; what is bought is a quit that reports the code it meant rather than
    a crash the listener has to read as one.
    """
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(code)


def left_with(code: int, window) -> int:
    """Leave with this code, having decided how to leave with it.

    Everything durable is already put away by the time this is asked. What is
    left to decide is whether the ordinary unwinding is safe. It is not while
    a cover lookup is still inside a read: see `leave_at_once`.
    """
    if window.lookups_in_flight:
        diary.note("a cover lookup is still reading; leaving without unwinding")
        leave_at_once(code)
    return code


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
    return left_with(code, window)
