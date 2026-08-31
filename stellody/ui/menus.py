"""The menu bar and the dialogs its entries open.

Kept apart from the window because they are a different kind of thing: the
window assembles the application and holds what it is made of, while this is
one long list of what a person can ask for. The two grow for different reasons
and neither should have to be read to change the other.

Every entry here repeats something a picture button already offers, so the
menus add reach rather than capability.
"""

from __future__ import annotations

from PySide6.QtCore import Slot
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QFileDialog, QMainWindow, QMenu

from stellody.shared import resources
from stellody.shared.version import APP_NAME, DONATE_URL
from stellody.ui.dialogs import AboutDialog, LicenceDialog
from stellody.ui.health import HealthDialog
from stellody.ui.links import open_externally
from stellody.ui.settings_keys import SETTING_ROOT, STATUS_TIMEOUT_MS


class Menus:
    """The window's half of offering everything it can be asked for."""

    def _build_menus(self) -> None:
        """The whole menu bar."""
        file_menu = self.menuBar().addMenu("&File")
        menu_action(file_menu, self, "Choose &music folder...", self.choose_folder)
        self._rescan_action = menu_action(file_menu, self, "&Rescan", self.rescan)
        file_menu.addSeparator()
        self._forget_close_action = menu_action(
            file_menu, self, "&Ask again when I close", self.forget_close_choice
        )
        file_menu.aboutToShow.connect(self._show_whether_a_choice_is_remembered)
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
    def _show_whether_a_choice_is_remembered(self) -> None:
        """Offer to forget only while there is something to forget."""
        self._forget_close_action.setEnabled(not self.asks_on_close)

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


def menu_action(menu: QMenu, window: QMainWindow, label: str, slot, checkable=False):
    """Add one action to a menu and return it."""
    action = QAction(label, window)
    action.setCheckable(checkable)
    action.triggered.connect(slot)
    menu.addAction(action)
    return action
