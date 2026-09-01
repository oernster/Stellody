"""The main window: menus, the album tree and the scan it is fed from."""

from __future__ import annotations

import itertools
import pathlib
import traceback
from collections.abc import Callable

from PySide6.QtCore import QSize, Qt, QTimer
from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
)

from stellody.application.artwork import AlbumArt
from stellody.application.choosing_covers import ChooseCover
from stellody.application.listening import ListeningLog
from stellody.application.ports import SettingsStore
from stellody.application.scan import (
    LoadLibrary,
)
from stellody.application.shapes import TrackShapes
from stellody.application.transport import Transport
from stellody.application.updates import UpdateService
from stellody.domain.health import LibraryIssue
from stellody.domain.track import Track
from stellody.shared.version import APP_NAME
from stellody.ui.appearance import Appearance
from stellody.ui.bottom_tray import BottomTray
from stellody.ui.choosing import Choosing
from stellody.ui.covering import Covering
from stellody.ui.geometry import Geometry
from stellody.ui.leaving import Leaving
from stellody.ui.menus import Menus
from stellody.ui.models import AlbumTreeModel
from stellody.ui.playing import TRANSPORT_POLL_MS, Playing
from stellody.ui.position_bar import PositionBar
from stellody.ui.rating import Rating
from stellody.ui.scanning import Scanning
from stellody.ui.searching import Searching
from stellody.ui.settings_keys import (
    FALSE,
    SETTING_DESCENDING,
    SETTING_ROOT,
    TRUE,
)
from stellody.ui.shape_worker import ShapeRunner
from stellody.ui.showing_shapes import ShowingShapes
from stellody.ui.showing_spectrum import ShowingSpectrum
from stellody.ui.toolbar import LibraryTray
from stellody.ui.transport_menu import TransportMenu
from stellody.ui.update_check import UpdateCheckController
from stellody.ui.viewing import Viewing
from stellody.ui.visualiser import Visualiser
from stellody.ui.window_parts import (
    application_icon,
    build_body,
    build_progress,
    build_tray,
    build_tree,
    neutral_holder,
)
from stellody.ui.worker import ScanRunner, ScanSession

# Enough frames to name the door without printing the whole interpreter.
TRAIL_FRAMES = 6
# The size the window opens at when nothing has been remembered, which is a
# first run and a stored value that is not a number. Widened by a tenth again,
# so the library gets the extra room rather than the strips: what the strips
# need is a floor the window is checked against, never the size it opens at.
# A window this wide is clamped to whatever screen it opens on, so a narrower
# monitor gets the screen rather than a window running off the edge of it.
WINDOW_WIDTH_PX = 1791
WINDOW_HEIGHT_PX = 864
TITLE_COLUMN_PX = 460
ARTIST_COLUMN_PX = 240


class _ForgetfulStore:
    """Stands in where nothing was given: it holds nothing and keeps nothing.

    A window built without a store still shows the stars, which is what every
    test that is not about ratings wants; what it says is simply never kept.
    """

    def all_listening(self) -> dict:
        """Nothing has ever been kept here."""
        return {}

    def set_listening(self, handle: str, path: str, record) -> None:
        """Take it and forget it."""


def _say_nothing(message: str) -> None:
    """The default diary: one that keeps no account at all."""


def _trail() -> str:
    """The calling frames, innermost last, on one line."""
    frames = traceback.extract_stack()[:-2]
    return " <- ".join(
        f"{pathlib.PurePath(frame.filename).name}:{frame.lineno} {frame.name}"
        for frame in frames[-TRAIL_FRAMES:]
    )


class MainWindow(
    Scanning,
    Searching,
    Playing,
    TransportMenu,
    Choosing,
    ShowingShapes,
    ShowingSpectrum,
    Menus,
    Rating,
    Geometry,
    Leaving,
    Covering,
    Appearance,
    Viewing,
    QMainWindow,
):
    """Stellody's window: a library, a menu bar and a status line."""

    def __init__(
        self,
        scan_session: ScanSession,
        loader: LoadLibrary,
        transport: Transport,
        settings: SettingsStore,
        shapes: TrackShapes | None = None,
        listening: ListeningLog | None = None,
        art: AlbumArt | None = None,
        chooser: ChooseCover | None = None,
        updates: UpdateService | None = None,
        leave: Callable[[], None] | None = None,
        note: Callable[[str], None] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        # Where the window writes down what happened to it. Injected because
        # the UI may not reach into infrastructure; a window given none keeps
        # its own counsel, which is what every test wants.
        self._note = note or _say_nothing
        # How the application is put down. Injected so a test can watch it
        # happen without the test run quitting itself; the running
        # application's own quit when nobody supplies one.
        self._leave = leave
        self._scan_session = scan_session
        # Built at the end of __init__, once there is a window to sit over.
        # A window given no service never checks and never offers, which is
        # what every test that is about something else wants.
        self._update_service = updates
        self._updates = None
        # A window without one still runs; it just has nothing to remember.
        self._listening = listening or ListeningLog(_ForgetfulStore())
        self._loader = loader
        self._transport = transport
        # The one thing here that is set rather than injected: the transport
        # is built before the window that can turn a track into its album.
        transport.report_plays_to(self.count_play)
        self._settings = settings
        self._issues: tuple[LibraryIssue, ...] = ()
        self._quitting = False
        self._started = False
        self._runner = ScanRunner(self)
        self._shapes = shapes
        self._shape_shown = None
        self._shape_runner = ShapeRunner(shapes, self) if shapes is not None else None
        self._model = AlbumTreeModel(self, listening=self._listening)
        self._neutral = neutral_holder(self)

        self.setWindowTitle(APP_NAME)
        self.resize(WINDOW_WIDTH_PX, WINDOW_HEIGHT_PX)
        icon = application_icon()
        if icon is not None:
            self.setWindowIcon(icon)
        self._tree = build_tree(self, self._model)
        self.start_covering(art)
        self.start_choosing(chooser)
        self.start_searching()
        self._tray = LibraryTray(
            self,
            choose_folder=self.choose_folder,
            toggle_search=self.toggle_search,
            search_changed=self.search_changed,
            search_again=self.search_again,
            toggle_theme=self.toggle_theme,
            show_about=self.show_about,
            check_for_updates=self.check_for_updates,
            toggle_mute=self.toggle_mute,
            set_volume=self.set_volume,
            previous_track=self.previous_track,
            toggle_playback=self.toggle_playback,
            stop_playback=self.stop_playback,
            next_track=self.next_track,
            toggle_view=self.toggle_view,
            toggle_cover_size=self.toggle_cover_size,
            open_equaliser=self.show_equaliser,
        )
        self._visualiser = Visualiser(self)
        self._visualiser.read_levels_from(lambda: self._transport.levels)
        self._position_bar = PositionBar(self, seek=self.seek_to)
        self._position_bar.stars.chosen.connect(self.rate_shown)
        self._bottom_tray = BottomTray(
            self,
            toggle_shuffle=self.toggle_shuffle,
            toggle_repeat=self.toggle_repeat,
            open_donation=self.open_donation,
            rescan=self.rescan,
            repair_library=self.repair_library,
        )
        self.setCentralWidget(
            build_body(
                self,
                self._tray,
                self.start_viewing(),
                self._visualiser,
                self._position_bar,
                self._bottom_tray,
            )
        )
        self._set_ring_order()
        self._progress = build_progress(self)
        self.statusBar().addPermanentWidget(self._progress)
        self._build_menus()
        self._notification = build_tray(self, icon)
        self._apply_theme(self.theme_mode)
        self._model.set_descending(self._flag(SETTING_DESCENDING))
        # The track the highlight was last moved to, so the library follows
        # the transport on a change rather than on every poll.
        self._followed: Track | None = None
        self.wire_tree()
        self.restore_volume()
        self.restore_switches()
        self.restore_view()
        self.restore_visualiser()
        self.restore_geometry(QSize(WINDOW_WIDTH_PX, WINDOW_HEIGHT_PX))
        self._tree.selectionModel().currentChanged.connect(self._on_selection)
        self._transport_timer = QTimer(self)
        self._transport_timer.timeout.connect(self._poll_transport)
        self._transport_timer.start(TRANSPORT_POLL_MS)
        self._show_transport()
        if self._shape_runner is not None:
            self._shape_runner.ready.connect(self._on_shape)
        self._runner.progressed.connect(self._on_progress)
        self._runner.completed.connect(self._on_completed)
        self._runner.failed.connect(self._on_failed)
        self._start_update_checks()

    def _start_update_checks(self) -> None:
        """Attach the update check, once there is a window for it to sit over.

        Last of all, because the controller starts a timer as it is built and
        the answer it eventually brings back wants a window to open a dialog
        over. A window given no service is left without one entirely rather
        than with a controller that would check nothing.
        """
        if self._update_service is None:
            return
        self._updates = UpdateCheckController(
            self._update_service,
            self._settings.get_setting,
            self._settings.set_setting,
            self,
        )

    def _set_ring_order(self) -> None:
        """Tab reaches the tray before the library, which is how they are drawn.

        Qt builds its chain in creation order; the tree is created first because
        the tray is handed it. Reading order is what the ring must
        follow, so it is stated rather than inherited.
        """
        stops = (
            *self._tray.ring_stops(),
            self._tree,
            self._grid,
            self._album_pane.album_stars,
            *self._album_pane.columns,
            self._position_bar.slider,
            self._position_bar.stars,
            *self._bottom_tray.ring_stops(),
        )
        for earlier, later in itertools.pairwise(stops):
            QWidget.setTabOrder(earlier, later)

    @property
    def library_root(self) -> str:
        """The music folder Stellody was last pointed at."""
        return self._settings.get_setting(SETTING_ROOT, "")

    def _flag(self, key: str, default: str = FALSE) -> bool:
        """A stored boolean setting.

        The default matters for a setting written by a version that did not
        have it: a library scanned before the finished marker existed is a
        finished one, not an interrupted one.
        """
        return self._settings.get_setting(key, default) == TRUE

    def showEvent(self, event) -> None:
        """Start with nothing highlighted, so no menu drops open on launch.

        Every appearance is written down with the frames that led to it. A
        window coming up unbidden is the fault under investigation; the stack
        is what names the door it came through, even when the door is one
        nobody thought to watch.
        """
        super().showEvent(event)
        self._note(f"window shown, first time: {not self._started} <- {_trail()}")
        if not self._started:
            self._started = True
            self._neutral.setFocus(Qt.FocusReason.OtherFocusReason)

    def hideEvent(self, event) -> None:
        """Note the window going away, so the log has both halves."""
        super().hideEvent(event)
        self._note("window hidden")
