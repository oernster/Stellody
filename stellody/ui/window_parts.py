"""How the window's parts are built.

Assembly only: each function returns one configured widget and holds no state,
so the window module is left to say what the window DOES rather than how its
pieces are put together.

Every container here is explicitly NoFocus. A pane holds controls; it is not one
of them, so it is never a stop and never paints a ring.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import (
    QHeaderView,
    QMainWindow,
    QMenu,
    QProgressBar,
    QSystemTrayIcon,
    QTreeView,
    QVBoxLayout,
    QWidget,
)

from stellody.shared import resources
from stellody.shared.version import APP_NAME
from stellody.ui.models import AlbumTreeModel, Column

TITLE_COLUMN_PX = 460
ARTIST_COLUMN_PX = 240
PROGRESS_WIDTH_PX = 160


def application_icon() -> QIcon | None:
    """The window and tray icon, when the asset resolves."""
    path = resources.application_icon_path() or resources.window_icon_path()
    if path is None:
        return None
    icon = QIcon(str(path))
    return None if icon.isNull() else icon


def build_body(window: QMainWindow, tray: QWidget, tree: QWidget) -> QWidget:
    """The tray above the library, as one central widget.

    A plain container: it holds the two of them and is never a stop itself.
    """
    holder = QWidget(window)
    holder.setFocusPolicy(Qt.FocusPolicy.NoFocus)
    column = QVBoxLayout(holder)
    column.setContentsMargins(0, 0, 0, 0)
    column.setSpacing(0)
    column.addWidget(tray)
    column.addWidget(tree, 1)
    return holder


def neutral_holder(window: QMainWindow) -> QWidget:
    """A zero-size focus holder, so no menu is highlighted on launch."""
    holder = QWidget(window)
    holder.setObjectName("NeutralStart")
    holder.setFixedSize(0, 0)
    holder.setFocusPolicy(Qt.FocusPolicy.TabFocus)
    return holder


def build_tree(window: QMainWindow, model: AlbumTreeModel) -> QTreeView:
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


def build_progress(window: QMainWindow) -> QProgressBar:
    """The scan indicator, which starts with nothing to count yet.

    It runs indeterminate until the first folder is reported, because the
    total is not known until the counting pass has finished, then fills as a
    real fraction of the folders there are.

    The number goes on the status line rather than on the bar. Measured: the
    muted text Qt would centre on the bar sits at 1.32 to 1 against the filled
    chunk in dark and 1.29 to 1 in light, so it would disappear exactly as the
    fill reached it. On the status line the same colour reads at better than
    seven to one.
    """
    progress = QProgressBar(window)
    progress.setRange(0, 0)
    progress.setMaximumWidth(PROGRESS_WIDTH_PX)
    progress.setTextVisible(False)
    progress.setVisible(False)
    return progress


def build_tray(window: QMainWindow, icon: QIcon | None) -> QSystemTrayIcon:
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


def _on_tray(window: QMainWindow, reason: QSystemTrayIcon.ActivationReason) -> None:
    """Restore the window when the tray icon is clicked."""
    if reason == QSystemTrayIcon.ActivationReason.Trigger:
        window.restore_from_tray()
