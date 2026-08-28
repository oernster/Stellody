"""The main window: menus, the album tree and the scan it is fed from."""

from __future__ import annotations

from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QAction, QCloseEvent, QIcon
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QHeaderView,
    QMainWindow,
    QMenu,
    QProgressBar,
    QSystemTrayIcon,
    QTreeView,
    QWidget,
)

from stellody.application.ports import SettingsStore
from stellody.application.scan import ScanLibrary, ScanReport
from stellody.domain.health import LibraryIssue
from stellody.shared import resources
from stellody.shared.version import APP_NAME
from stellody.ui.close_prompt import CloseAction, ClosePrompt
from stellody.ui.dialogs import AboutDialog, LicenceDialog
from stellody.ui.health import HealthDialog, has_serious_issues
from stellody.ui.models import AlbumTreeModel, Column
from stellody.ui.theme import Mode, stylesheet
from stellody.ui.worker import ScanRunner

SETTING_THEME = "theme"
SETTING_ROOT = "library_root"
SETTING_CLOSE = "close_action"
SETTING_DESCENDING = "sort_descending"

WINDOW_WIDTH_PX = 1080
WINDOW_HEIGHT_PX = 720
TITLE_COLUMN_PX = 460
ARTIST_COLUMN_PX = 240
STATUS_TIMEOUT_MS = 6000
TRUE = "1"
FALSE = "0"


class MainWindow(QMainWindow):
    """Stellody's window: a library, a menu bar and a status line."""

    def __init__(
        self,
        scanner: ScanLibrary,
        settings: SettingsStore,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._scanner = scanner
        self._settings = settings
        self._issues: tuple[LibraryIssue, ...] = ()
        self._quitting = False
        self._started = False
        self._runner = ScanRunner(self)
        self._model = AlbumTreeModel(self)
        self._neutral = _neutral_holder(self)

        self.setWindowTitle(APP_NAME)
        self.resize(WINDOW_WIDTH_PX, WINDOW_HEIGHT_PX)
        icon = _application_icon()
        if icon is not None:
            self.setWindowIcon(icon)
        self._tree = _build_tree(self, self._model)
        self.setCentralWidget(self._tree)
        self._progress = _build_progress(self)
        self.statusBar().addPermanentWidget(self._progress)
        self._build_menus()
        self._tray = _build_tray(self, icon)
        self._apply_theme(self.theme_mode)
        self._model.set_descending(self._flag(SETTING_DESCENDING))
        self._runner.progressed.connect(self._on_progress)
        self._runner.completed.connect(self._on_completed)
        self._runner.failed.connect(self._on_failed)

    @property
    def theme_mode(self) -> Mode:
        """The appearance currently stored."""
        stored = self._settings.get_setting(SETTING_THEME, Mode.DARK.value)
        return Mode(stored) if stored in tuple(Mode) else Mode.DARK

    @property
    def library_root(self) -> str:
        """The music folder Stellody was last pointed at."""
        return self._settings.get_setting(SETTING_ROOT, "")

    def _flag(self, key: str) -> bool:
        """A stored boolean setting."""
        return self._settings.get_setting(key, FALSE) == TRUE

    def showEvent(self, event) -> None:
        """Start with nothing highlighted, so no menu drops open on launch."""
        super().showEvent(event)
        if not self._started:
            self._started = True
            self._neutral.setFocus(Qt.FocusReason.OtherFocusReason)

    def _build_menus(self) -> None:
        """The whole menu bar."""
        file_menu = self.menuBar().addMenu("&File")
        _add(file_menu, self, "Choose &music folder...", self.choose_folder)
        self._rescan_action = _add(file_menu, self, "&Rescan", self.rescan)
        file_menu.addSeparator()
        _add(file_menu, self, "&Quit", self.quit_application)

        view_menu = self.menuBar().addMenu("&View")
        self._light_action = _add(
            view_menu, self, "&Light appearance", self.use_light, checkable=True
        )
        self._dark_action = _add(
            view_menu, self, "&Dark appearance", self.use_dark, checkable=True
        )
        view_menu.addSeparator()
        self._descending_action = _add(
            view_menu, self, "Sort &Z to A", self.toggle_order, checkable=True
        )
        view_menu.addSeparator()
        _add(view_menu, self, "&Expand all", self._tree.expandAll)
        _add(view_menu, self, "&Collapse all", self._tree.collapseAll)

        help_menu = self.menuBar().addMenu("&Help")
        _add(help_menu, self, "Library &health...", self.show_health)
        help_menu.addSeparator()
        _add(help_menu, self, "&Model licence (GPL-3.0)", self.show_model_licence)
        _add(help_menu, self, "&UI licence (LGPL-3.0)", self.show_ui_licence)
        help_menu.addSeparator()
        _add(help_menu, self, f"&About {APP_NAME}", self.show_about)

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
    def rescan(self) -> None:
        """Scan the remembered folder again."""
        self.start_scan()

    def start_scan(self) -> bool:
        """Begin scanning the remembered folder; False when it cannot start."""
        root = self.library_root
        if not root:
            self.statusBar().showMessage(
                "Choose a music folder to begin.", STATUS_TIMEOUT_MS
            )
            return False
        if not self._runner.start(self._scanner, root):
            return False
        self._rescan_action.setEnabled(False)
        self._progress.setVisible(True)
        self.statusBar().showMessage(f"Scanning {root}")
        return True

    @Slot(str)
    def _on_progress(self, folder: str) -> None:
        """Show which folder is being read."""
        self.statusBar().showMessage(folder)

    @Slot(object)
    def _on_completed(self, report: ScanReport) -> None:
        """Show the finished library."""
        self._issues = report.issues
        self._model.set_albums(report.albums)
        self._progress.setVisible(False)
        self._rescan_action.setEnabled(True)
        self.statusBar().showMessage(_summary(report), STATUS_TIMEOUT_MS)

    @Slot(str)
    def _on_failed(self, message: str) -> None:
        """Report a scan that could not finish."""
        self._progress.setVisible(False)
        self._rescan_action.setEnabled(True)
        self.statusBar().showMessage(f"Scan failed: {message}")

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
        HealthDialog(self._issues, self).exec()

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
    def quit_application(self) -> None:
        """Leave, whatever the close button is set to do."""
        self._quitting = True
        self.close()

    def closeEvent(self, event: QCloseEvent) -> None:
        """Honour the stored close behaviour, asking when none is stored."""
        if self._quitting or not self._tray.isVisible():
            self._runner.wait()
            event.accept()
            return
        action = self._settings.get_setting(SETTING_CLOSE, CloseAction.ASK.value)
        if action == CloseAction.ASK.value:
            action = self._ask_close_action()
        if action == CloseAction.QUIT.value:
            self._quitting = True
            self._runner.wait()
            event.accept()
            return
        event.ignore()
        self.hide()

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
        return self._tray.isVisible()

    @Slot()
    def restore_from_tray(self) -> None:
        """Bring the window back from the system tray."""
        self.showNormal()
        self.raise_()
        self.activateWindow()


def _summary(report: ScanReport) -> str:
    """The one-line result of a scan."""
    parts = [
        f"{len(report.albums)} albums",
        f"{report.track_count} tracks",
        f"{report.files_probed} files",
    ]
    if report.files_absent:
        parts.append(f"{report.files_absent} missing")
    if has_serious_issues(report.issues):
        parts.append(f"{len(report.issues)} issues, see Help then Library health")
    return "  |  ".join(parts)


def _add(menu: QMenu, window: QMainWindow, label: str, slot, checkable=False):
    """Add one action to a menu and return it."""
    action = QAction(label, window)
    action.setCheckable(checkable)
    action.triggered.connect(slot)
    menu.addAction(action)
    return action


def _application_icon() -> QIcon | None:
    """The window and tray icon, when the asset resolves."""
    path = resources.application_icon_path() or resources.window_icon_path()
    if path is None:
        return None
    icon = QIcon(str(path))
    return None if icon.isNull() else icon


def _neutral_holder(window: QMainWindow) -> QWidget:
    """A zero-size focus holder, so no menu is highlighted on launch."""
    holder = QWidget(window)
    holder.setFixedSize(0, 0)
    holder.setFocusPolicy(Qt.FocusPolicy.TabFocus)
    return holder


def _build_tree(window: QMainWindow, model: AlbumTreeModel) -> QTreeView:
    """The album tree, configured for a large library."""
    tree = QTreeView(window)
    tree.setModel(model)
    tree.setUniformRowHeights(True)
    tree.setAlternatingRowColors(True)
    tree.setAllColumnsShowFocus(True)
    tree.setSelectionBehavior(QTreeView.SelectionBehavior.SelectRows)
    tree.setExpandsOnDoubleClick(True)
    tree.setRootIsDecorated(True)
    header = tree.header()
    header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
    header.setStretchLastSection(False)
    header.setSectionResizeMode(Column.DETAIL, QHeaderView.ResizeMode.Stretch)
    tree.setColumnWidth(Column.TITLE, TITLE_COLUMN_PX)
    tree.setColumnWidth(Column.ARTIST, ARTIST_COLUMN_PX)
    return tree


def _build_progress(window: QMainWindow) -> QProgressBar:
    """The indeterminate scan indicator."""
    progress = QProgressBar(window)
    progress.setRange(0, 0)
    progress.setMaximumWidth(160)
    progress.setTextVisible(False)
    progress.setVisible(False)
    return progress


def _build_tray(window: MainWindow, icon: QIcon | None) -> QSystemTrayIcon:
    """The system tray presence and its menu."""
    tray = QSystemTrayIcon(window)
    if icon is not None:
        tray.setIcon(icon)
    tray.setToolTip(APP_NAME)
    menu = QMenu()
    show = QAction(f"Show {APP_NAME}", menu)
    show.triggered.connect(window.restore_from_tray)
    menu.addAction(show)
    menu.addSeparator()
    quit_action = QAction("Quit", menu)
    quit_action.triggered.connect(window.quit_application)
    menu.addAction(quit_action)
    tray.setContextMenu(menu)
    tray.activated.connect(lambda reason: _on_tray(window, reason))
    if QSystemTrayIcon.isSystemTrayAvailable():
        tray.show()
    return tray


def _on_tray(window: MainWindow, reason: QSystemTrayIcon.ActivationReason) -> None:
    """Restore the window when the tray icon is clicked."""
    if reason == QSystemTrayIcon.ActivationReason.Trigger:
        window.restore_from_tray()
