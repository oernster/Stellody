"""The main window: menus, the album tree and the scan it is fed from."""

from __future__ import annotations

import itertools
from collections.abc import Callable

from PySide6.QtCore import Qt, QTimer, Slot
from PySide6.QtGui import QAction, QCloseEvent
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QMainWindow,
    QMenu,
    QWidget,
)

from stellody.application.ports import SettingsStore
from stellody.application.scan import (
    LoadLibrary,
)
from stellody.application.transport import Transport
from stellody.domain.health import LibraryIssue
from stellody.domain.track import Track
from stellody.shared import resources
from stellody.shared.version import APP_NAME, DONATE_URL
from stellody.ui.bottom_tray import BottomTray
from stellody.ui.close_prompt import CloseAction, ClosePrompt
from stellody.ui.dialogs import AboutDialog, LicenceDialog
from stellody.ui.health import HealthDialog
from stellody.ui.links import open_externally
from stellody.ui.models import AlbumTreeModel
from stellody.ui.playing import TRANSPORT_POLL_MS, Playing
from stellody.ui.scanning import Scanning
from stellody.ui.settings_keys import (
    FALSE,
    SETTING_CLOSE,
    SETTING_DESCENDING,
    SETTING_ROOT,
    SETTING_THEME,
    STATUS_TIMEOUT_MS,
    TRUE,
)
from stellody.ui.theme import Mode, stylesheet
from stellody.ui.toolbar import LibraryTray
from stellody.ui.window_parts import (
    application_icon,
    build_body,
    build_progress,
    build_tray,
    build_tree,
    neutral_holder,
)
from stellody.ui.worker import ScanRunner, ScanSession

WINDOW_WIDTH_PX = 1080
WINDOW_HEIGHT_PX = 720
TITLE_COLUMN_PX = 460
ARTIST_COLUMN_PX = 240


class MainWindow(Scanning, Playing, QMainWindow):
    """Stellody's window: a library, a menu bar and a status line."""

    def __init__(
        self,
        scan_session: ScanSession,
        loader: LoadLibrary,
        transport: Transport,
        settings: SettingsStore,
        leave: Callable[[], None] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        # How the application is put down. Injected so a test can watch it
        # happen without the test run quitting itself; the running
        # application's own quit when nobody supplies one.
        self._leave = leave
        self._scan_session = scan_session
        self._loader = loader
        self._transport = transport
        self._settings = settings
        self._issues: tuple[LibraryIssue, ...] = ()
        self._quitting = False
        self._started = False
        self._runner = ScanRunner(self)
        self._model = AlbumTreeModel(self)
        self._neutral = neutral_holder(self)

        self.setWindowTitle(APP_NAME)
        self.resize(WINDOW_WIDTH_PX, WINDOW_HEIGHT_PX)
        icon = application_icon()
        if icon is not None:
            self.setWindowIcon(icon)
        self._tree = build_tree(self, self._model)
        self._tray = LibraryTray(
            self,
            choose_folder=self.choose_folder,
            rescan=self.rescan,
            toggle_theme=self.toggle_theme,
            show_about=self.show_about,
            toggle_mute=self.toggle_mute,
            previous_track=self.previous_track,
            toggle_playback=self.toggle_playback,
            stop_playback=self.stop_playback,
            next_track=self.next_track,
        )
        self._bottom_tray = BottomTray(
            self,
            on_change=self.set_volume,
            toggle_shuffle=self.toggle_shuffle,
            toggle_repeat=self.toggle_repeat,
            open_donation=self.open_donation,
            repair_library=self.repair_library,
        )
        self.setCentralWidget(
            build_body(self, self._tray, self._tree, self._bottom_tray)
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
        self._tree.selectionModel().currentChanged.connect(self._on_selection)
        self._transport_timer = QTimer(self)
        self._transport_timer.timeout.connect(self._poll_transport)
        self._transport_timer.start(TRANSPORT_POLL_MS)
        self._show_transport()
        self._runner.progressed.connect(self._on_progress)
        self._runner.completed.connect(self._on_completed)
        self._runner.failed.connect(self._on_failed)

    def _set_ring_order(self) -> None:
        """Tab reaches the tray before the library, which is how they are drawn.

        Qt builds its chain in creation order; the tree is created first because
        the tray is handed it. Reading order is what the ring must
        follow, so it is stated rather than inherited.
        """
        stops = (
            *self._tray.ring_stops(),
            self._tree,
            *self._bottom_tray.ring_stops(),
        )
        for earlier, later in itertools.pairwise(stops):
            QWidget.setTabOrder(earlier, later)

    @property
    def theme_mode(self) -> Mode:
        """The appearance currently stored."""
        stored = self._settings.get_setting(SETTING_THEME, Mode.DARK.value)
        return Mode(stored) if stored in tuple(Mode) else Mode.DARK

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
        """Start with nothing highlighted, so no menu drops open on launch."""
        super().showEvent(event)
        if not self._started:
            self._started = True
            self._neutral.setFocus(Qt.FocusReason.OtherFocusReason)

    def _build_menus(self) -> None:
        """The whole menu bar."""
        file_menu = self.menuBar().addMenu("&File")
        menu_action(file_menu, self, "Choose &music folder...", self.choose_folder)
        self._rescan_action = menu_action(file_menu, self, "&Rescan", self.rescan)
        file_menu.addSeparator()
        menu_action(file_menu, self, "&Quit", self.quit_application)

        view_menu = self.menuBar().addMenu("&View")
        self._light_action = menu_action(
            view_menu, self, "&Light appearance", self.use_light, checkable=True
        )
        self._dark_action = menu_action(
            view_menu, self, "&Dark appearance", self.use_dark, checkable=True
        )
        view_menu.addSeparator()
        self._descending_action = menu_action(
            view_menu, self, "Sort &Z to A", self.toggle_order, checkable=True
        )
        view_menu.addSeparator()
        menu_action(view_menu, self, "&Expand all", self._tree.expandAll)
        menu_action(view_menu, self, "&Collapse all", self._tree.collapseAll)

        help_menu = self.menuBar().addMenu("&Help")
        menu_action(help_menu, self, "Library &health...", self.show_health)
        help_menu.addSeparator()
        menu_action(
            help_menu, self, "&Model licence (GPL-3.0)", self.show_model_licence
        )
        menu_action(help_menu, self, "&UI licence (LGPL-3.0)", self.show_ui_licence)
        help_menu.addSeparator()
        menu_action(help_menu, self, f"&About {APP_NAME}", self.show_about)

    @Slot()
    def choose_folder(self) -> None:
        """Ask for a music folder, remember it and scan it."""
        chosen = QFileDialog.getExistingDirectory(
            self, "Choose your music folder", self.library_root
        )
        if not chosen:
            return
        self._settings.set_setting(SETTING_ROOT, chosen)
        self.start_scan()

    @Slot()
    def toggle_theme(self) -> None:
        """Swap between the two appearances, from the tray."""
        self._apply_theme(Mode.LIGHT if self.theme_mode is Mode.DARK else Mode.DARK)

    @Slot()
    def use_light(self) -> None:
        """Switch to the light appearance."""
        self._apply_theme(Mode.LIGHT)

    @Slot()
    def use_dark(self) -> None:
        """Switch to the dark appearance."""
        self._apply_theme(Mode.DARK)

    def _apply_theme(self, mode: Mode) -> None:
        """Paint the application in one appearance and remember the choice."""
        self._settings.set_setting(SETTING_THEME, mode.value)
        application = QApplication.instance()
        if application is not None:
            application.setStyleSheet(stylesheet(mode))
        self._light_action.setChecked(mode is Mode.LIGHT)
        self._dark_action.setChecked(mode is Mode.DARK)
        self._tray.set_mode(mode)

    @Slot()
    def toggle_order(self) -> None:
        """Invert the album order and remember it."""
        descending = not self._model.descending
        self._model.set_descending(descending)
        self._descending_action.setChecked(descending)
        self._settings.set_setting(SETTING_DESCENDING, TRUE if descending else FALSE)

    @Slot()
    def show_health(self) -> None:
        """Open the library health report."""
        HealthDialog(self._issues, self, repair_library=self.repair_library).exec()

    @Slot()
    def repair_library(self) -> None:
        """Accept the corrections the health report describes.

        Nothing here yet. Resolution already happens on load, so what each
        issue should become is worked out on every start; what is missing is
        somewhere to keep an accepted correction. The buttons that would call
        this are disabled until there is, so this is the seam rather than the
        feature.
        """

    @Slot()
    def show_model_licence(self) -> None:
        """Open the GPL-3.0 text."""
        LicenceDialog(
            "Model licence (GPL-3.0)", resources.model_licence_path(), self
        ).exec()

    @Slot()
    def show_ui_licence(self) -> None:
        """Open the LGPL-3.0 text."""
        LicenceDialog("UI licence (LGPL-3.0)", resources.ui_licence_path(), self).exec()

    @Slot()
    def show_about(self) -> None:
        """Open the About dialog."""
        AboutDialog(self).exec()

    @Slot()
    def open_donation(self) -> None:
        """Hand the donation page to whatever the desktop opens links with.

        Stellody opens no connection of its own here. The address goes outward
        and the browser does the asking, which is why the local-first
        guarantee is unchanged by this button existing.

        A desktop that declines to open it says so in the status bar. Silence
        would leave the user pressing a button that appears to do nothing.
        """
        if not open_externally(DONATE_URL):
            self.statusBar().showMessage(
                "Could not open a browser for the donation page",
                STATUS_TIMEOUT_MS,
            )

    @Slot()
    def quit_application(self) -> None:
        """Leave, whatever the close button is set to do."""
        self._quitting = True
        self.close()

    def closeEvent(self, event: QCloseEvent) -> None:
        """Honour the stored close behaviour, asking when none is stored."""
        if self._quitting or not self._notification.isVisible():
            self._leave_for_good(event)
            return
        action = self._settings.get_setting(SETTING_CLOSE, CloseAction.ASK.value)
        if action == CloseAction.ASK.value:
            action = self._ask_close_action()
        if action == CloseAction.QUIT.value:
            self._quitting = True
            self._leave_for_good(event)
            return
        event.ignore()
        self.hide()

    def _leave_for_good(self, event: QCloseEvent) -> None:
        """Put the work down, then put the application down with it.

        Ending the application has to be said out loud here. Quitting when the
        last window closes is deliberately off, since that is what lets the
        cross leave Stellody in the notification area; the cost is that
        nothing then ends the event loop by itself. Without this the tray's
        Quit closed a window nobody could see and left the process running,
        still holding the tray icon and the claim to being the copy that runs,
        so the one control that should have stopped Stellody could not.
        """
        self._transport_timer.stop()
        self._transport.stop()
        self._runner.wait()
        event.accept()
        depart = self._leave or QApplication.quit
        depart()

    def _ask_close_action(self) -> str:
        """Ask what closing should mean, defaulting to staying in the tray."""
        prompt = ClosePrompt(self)
        prompt.exec()
        if prompt.remember:
            self._settings.set_setting(SETTING_CLOSE, prompt.choice.value)
        return prompt.choice.value

    @property
    def tray_active(self) -> bool:
        """True when there is a tray icon to restore the window from.

        Starting hidden is only honest while this holds; without a tray there
        would be nothing on screen at all.
        """
        return self._notification.isVisible()

    @Slot()
    def restore_from_tray(self) -> None:
        """Bring the window back from the system tray."""
        self.showNormal()
        self.raise_()
        self.activateWindow()


def menu_action(menu: QMenu, window: QMainWindow, label: str, slot, checkable=False):
    """Add one action to a menu and return it."""
    action = QAction(label, window)
    action.setCheckable(checkable)
    action.triggered.connect(slot)
    menu.addAction(action)
    return action
