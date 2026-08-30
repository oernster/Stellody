"""How the window's parts are built.

Assembly only: each function returns one configured widget and holds no state,
so the window module is left to say what the window DOES rather than how its
pieces are put together.

Every container here is explicitly NoFocus. A pane holds controls; it is not one
of them, so it is never a stop and never paints a ring.
"""

from __future__ import annotations

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import (
    QHeaderView,
    QListView,
    QMainWindow,
    QMenu,
    QProgressBar,
    QStackedWidget,
    QSystemTrayIcon,
    QTreeView,
    QVBoxLayout,
    QWidget,
)

from stellody.shared import resources
from stellody.shared.version import APP_NAME
from stellody.ui.models import AlbumTreeModel, Column
from stellody.ui.tiles import TILE_HEIGHT_PX, TILE_WIDTH_PX, AlbumTile

# The gap between tiles. A tile's own size is the delegate's, so the two
# cannot drift apart when one of them is changed.
GRID_GAP_PX = 12
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


def build_body(
    window: QMainWindow,
    tray: QWidget,
    tree: QWidget,
    position: QWidget,
    footer: QWidget,
) -> QWidget:
    """The toolbar, the library, the position bar, then the volume strip.

    A plain container: it holds them and is never a stop itself.
    """
    holder = QWidget(window)
    holder.setFocusPolicy(Qt.FocusPolicy.NoFocus)
    column = QVBoxLayout(holder)
    column.setContentsMargins(0, 0, 0, 0)
    column.setSpacing(0)
    column.addWidget(tray)
    column.addWidget(tree, 1)
    column.addWidget(position)
    column.addWidget(footer)
    return holder


class _NeutralStart(QWidget):
    """A zero-size focus holder that leaves the ring once it has been left.

    Something has to hold focus at launch or Qt gives it to the first control,
    which highlights a menu title before the user has asked for anything. This
    takes it instead, then drops out of the tab chain the moment focus moves on,
    so the cycle that follows holds only real controls: without that, tabbing
    around the window lands once per lap on a widget nobody can see.
    """

    def focusOutEvent(self, event) -> None:
        """Leave the ring, having done the one job there was."""
        super().focusOutEvent(event)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)


def neutral_holder(window: QMainWindow) -> QWidget:
    """A zero-size focus holder, so no menu is highlighted on launch."""
    holder = _NeutralStart(window)
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


def build_grid(window: QMainWindow, model: AlbumTreeModel) -> QListView:
    """The album covers, laid out as a grid over the same model as the tree.

    A list view over a tree model shows the root's children, which is exactly
    the albums, so the two views cannot disagree about what the library holds
    or about the order it is in.
    """
    grid = QListView(window)
    grid.setModel(model)
    grid.setModelColumn(Column.TITLE)
    grid.setViewMode(QListView.ViewMode.IconMode)
    grid.setFlow(QListView.Flow.LeftToRight)
    grid.setWrapping(True)
    grid.setResizeMode(QListView.ResizeMode.Adjust)
    grid.setMovement(QListView.Movement.Static)
    grid.setUniformItemSizes(True)
    grid.setItemDelegate(AlbumTile(grid))
    grid.setGridSize(QSize(TILE_WIDTH_PX + GRID_GAP_PX, TILE_HEIGHT_PX + GRID_GAP_PX))
    return grid


def build_covers_page(window: QMainWindow, grid: QWidget, pane: QWidget) -> QWidget:
    """The grid with the album pane under it, which starts closed."""
    page = QWidget(window)
    page.setFocusPolicy(Qt.FocusPolicy.NoFocus)
    column = QVBoxLayout(page)
    column.setContentsMargins(0, 0, 0, 0)
    column.setSpacing(0)
    column.addWidget(grid, 1)
    column.addWidget(pane)
    return page


def build_library(window: QMainWindow, tree: QWidget, grid: QWidget) -> QStackedWidget:
    """The two library views, one showing at a time.

    A plain holder: it never takes focus and never wears a ring, so the view
    inside it is the stop rather than the box around it.
    """
    stack = QStackedWidget(window)
    stack.setFocusPolicy(Qt.FocusPolicy.NoFocus)
    stack.addWidget(tree)
    stack.addWidget(grid)
    return stack


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


ASK_ON_CLOSE_LABEL = "Ask again when I close"


def build_tray(window: QMainWindow, icon: QIcon | None) -> QSystemTrayIcon:
    """The system tray presence and its menu."""
    tray = QSystemTrayIcon(window)
    if icon is not None:
        tray.setIcon(icon)
    tray.setToolTip(APP_NAME)
    menu = QMenu()
    show = QAction(f"Show {APP_NAME}", menu)
    show.triggered.connect(window.restore_for_tray_menu)
    menu.addAction(show)
    menu.addSeparator()
    forget = QAction(ASK_ON_CLOSE_LABEL, menu)
    forget.triggered.connect(window.forget_close_choice)
    menu.addAction(forget)
    menu.aboutToShow.connect(lambda: forget.setEnabled(not window.asks_on_close))
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
        window.restore_for_tray_icon()
