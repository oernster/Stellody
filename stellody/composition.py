"""The composition root: the one place that wires infrastructure to the UI.

This module sits above the layer boundaries on purpose. Nothing else in the
package is allowed to reach both sides.
"""

from __future__ import annotations

import os
import sys
import time
import traceback
from collections.abc import Callable

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from stellody.application.artwork import AlbumArt
from stellody.application.choosing_covers import ChooseCover
from stellody.application.compilation_cost import CompilationCost
from stellody.application.discovering import Discovery
from stellody.application.editing import TagEditing
from stellody.application.expanding import Expansion
from stellody.application.listening import ListeningLog
from stellody.application.loading import LoadLibrary
from stellody.application.pictures import Pictures
from stellody.application.repairs import Repairs
from stellody.application.scan import ScanLibrary
from stellody.application.shapes import TrackShapes
from stellody.application.shop_editing import ShopEditing
from stellody.application.shopping import Shopping
from stellody.application.transport import Transport
from stellody.application.updates import UpdateService, platform_key_for
from stellody.infrastructure import (
    catalogue_memory,
    diary,
    discovery_file,
    instance,
    output,
    qt_messages,
    switch_reset,
    window_reset,
)
from stellody.infrastructure.artwork import FileArtwork
from stellody.infrastructure.audio import WasapiPlayback
from stellody.infrastructure.browsing import SystemBrowser, SystemClipboard
from stellody.infrastructure.catalogue import MusicBrainz
from stellody.infrastructure.courtesy import REQUEST_GAP_S, Gate
from stellody.infrastructure.cover_search import ArchiveCovers
from stellody.infrastructure.covers import EmbeddedPictures
from stellody.infrastructure.dropouts import DropoutWatch
from stellody.infrastructure.fetching import Fetcher
from stellody.infrastructure.opening import open_store
from stellody.infrastructure.output_devices import OutputDevices
from stellody.infrastructure.paths import (
    art_cache_dir,
    data_location,
    database_path,
    shape_cache_dir,
)
from stellody.infrastructure.probe import AudioProbe
from stellody.infrastructure.shop_file import FileShopBook, FileShopList
from stellody.infrastructure.similarity import ListenBrainz
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
from stellody.ui.geometry import forget_window
from stellody.ui.interface_scale import use_interface_scale
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
    source. Those two, the fetcher the catalogues ask through and the channel a
    second launch speaks over are the four modules able to open a connection;
    `tests/structural/test_offline.py` says so rather than a comment.
    """
    # One gate per host rather than per client: a gap owed to MusicBrainz is
    # owed by everything that asks it anything, so the run, an expansion and
    # the cover search share this one.
    gate = Gate()
    catalogue = MusicBrainz(Fetcher(gate))
    # One memory of what the catalogues said, shared by the run, its price
    # and the expansion, so its lock is the one lock over the one file.
    recall = catalogue_memory.FileCatalogueMemory()
    artwork = FileArtwork(art_cache_dir(), EmbeddedPictures())
    listening = ListeningLog(store)
    listening.load()
    # Every stream is opened through this, so one that follows a move of the
    # system's output is opened where the output went.
    devices = OutputDevices()
    window = MainWindow(
        scan_session=scan_session(store.database),
        loader=LoadLibrary(store),
        # Every block the device ran dry before it arrived goes into the
        # diary, so static heard under load can be matched to a line.
        transport=Transport(
            WasapiPlayback(
                opener=devices.open_output,
                dropouts=DropoutWatch(diary.note),
                rates=devices.exclusive_rates,
            )
        ),
        settings=store,
        # The platform question is asked HERE, where infrastructure may be
        # reached; the answer then travels as a value the window can show.
        exclusive_refusal=(
            "" if output.offers_exclusive() else output.NO_EXCLUSIVE_ON_LINUX
        ),
        shapes=TrackShapes(FileWaveforms(shape_cache_dir())),
        listening=listening,
        art=AlbumArt(artwork),
        chooser=ChooseCover(ArchiveCovers(gate), artwork),
        repairs=Repairs(store),
        tag_editing=TagEditing(store),
        pictures=Pictures(VideoReader),
        # Two services rather than one because neither catalogue answers both
        # questions; two gates rather than one because a gap owed to one
        # host says nothing about the other.
        discovery=Discovery(
            catalogue=catalogue,
            similarity=ListenBrainz(Fetcher()),
            pause=time.sleep,
            # What a candidate plays does not change between runs, while
            # asking costs a second each at the rate the catalogue permits.
            memory=discovery_file.FileGenreMemory(),
            # What either catalogue has already said, so a second run over the
            # same library gives the same answer rather than whatever the
            # service felt like that minute. Shared with the expansion below,
            # so an artist opened once is known to the next run as well.
            recall=recall,
        ),
        write_discovery=discovery_file.write,
        # What including compilations would add to a run, priced before it is
        # asked for. Read from the same memory the run reads, at the same gap
        # the catalogue's client is paced to, so the price and the run cannot
        # disagree about either. FR-D52.
        compilation_cost=CompilationCost(
            recall=recall,
            request_gap_s=REQUEST_GAP_S,
        ),
        # What the results dialog is made of: the file read back, plus the one
        # question a candidate artist is worth asking. The expansion is given
        # its own client over the SAME gate, so the two cannot come to ask
        # MusicBrainz twice inside the gap its terms require while a run is
        # still going on behind an open dialog.
        discovery_results=discovery_file.FileDiscoveryResults(),
        # What the results screen's genre filter judges a candidate by: the
        # same file the run keeps its answers in, read afresh each time the
        # screen opens. FR-D54.
        genre_memory=discovery_file.FileGenreMemory(),
        expansion=Expansion(
            catalogue=MusicBrainz(Fetcher(gate)),
            pause=time.sleep,
            recall=recall,
        ),
        # Taking a ticked album to a shop. Nothing here opens a connection:
        # the browser is handed an address and does the asking itself, which
        # is why this needs no entry in the offline test's list.
        shopping=Shopping(
            shops=FileShopList(),
            opener=SystemBrowser(),
            clipboard=SystemClipboard(),
            editing=ShopEditing(store=FileShopBook(), opener=SystemBrowser()),
        ),
        updates=UpdateService(
            GitHubReleases(), __version__, platform_key_for(sys.platform)
        ),
        leave=leave,
        note=note,
    )
    # Owned by the window, so it lives exactly as long as there is music to
    # pause; a move of the output pauses it and says so.
    devices.setParent(window)
    devices.changed.connect(window.output_moved)
    return window


def configure(application: QApplication) -> None:
    """Give the application its identity, its icon and its quick tooltips."""
    show_tips_quickly(application)
    application.setApplicationName(APP_NAME)
    # The display name is deliberately NOT set. Reported by Oliver on
    # 2026-09-09: the results screen wore an em dash in its title bar on Linux
    # and nowhere else. Qt's Linux platform plugins hand every window title to
    # `QPlatformWindow::formatWindowTitle`, which joins the title to the
    # display name with an em dash, so setting it made Qt write a character
    # this project bans into a title no source file here contains. The Windows
    # plugin does not append it, which is why it showed on one platform only,
    # and the main window escaped because Qt skips a title equal to the name.
    # Nothing else read the display name; the application name still carries
    # the identity.
    application.setApplicationVersion(__version__)
    application.setOrganizationName(APP_AUTHOR)
    application.setQuitOnLastWindowClosed(False)
    icon_path = resources.application_icon_path() or resources.window_icon_path()
    if icon_path is not None:
        application.setWindowIcon(QIcon(str(icon_path)))


def leave_at_once(code: int) -> None:
    """End the process where unwinding would end it worse.

    A cover lookup is given up within a slice of a second now: the archive
    asks whether anybody still wants it between its waits and inside its reads.
    What no amount of asking covers is a socket that never comes back at all.
    A thread still running when the application is torn down is one Qt ends the
    process over: measured on 2026-09-05, `QThread: Destroyed while thread
    is still running` from Qt6Core, an abort rather than an exit.

    So this is the last resort rather than the ordinary path. It should never
    be reached now; if it is, the alternative it replaces is a crash report.

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
    # Before the application, so a complaint made while it is being built is
    # written down too. A packaged copy has no console for these to reach.
    qt_messages.listen()
    diary.note(f"launched with {arguments[1:]}")
    # Before the application, since Qt reads the scale as it is built.
    use_interface_scale(os.environ)
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
    # Setup names the screen it was on after a fresh install, a repair or a
    # reinstall; the window opens maximised there, whatever size was left.
    afresh = window_reset.take(data_location())
    if afresh is not None:
        forget_window(store)
    window = build_window(store, application.quit, diary.note)
    if afresh is not None:
        placed = window.open_on(afresh.name, afresh.origin)
        diary.note(f"opened afresh where setup was, screen found: {placed}")
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
