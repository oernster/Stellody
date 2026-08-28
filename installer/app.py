"""The Stellody setup program.

A thin shell over installer.actions, wearing the application's own palette.
Every step is written to a log beside the install, because the worst installer
failures are the ones that never raise.
"""

from __future__ import annotations

import pathlib
import sys
import tempfile
import traceback

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QStackedWidget,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from installer import actions
from stellody.shared import resources
from stellody.shared.version import read_version
from stellody.ui.dialogs import LicenceDialog
from stellody.ui.theme import Mode, stylesheet

WINDOW_WIDTH_PX = 620
WINDOW_HEIGHT_PX = 480
BADGE_PX = 88
LOG_NAME = "stellody-setup.log"


class StepLog:
    """A plain record of what the setup program did, in order."""

    def __init__(self) -> None:
        self.path = pathlib.Path(tempfile.gettempdir()) / LOG_NAME
        self.lines: list[str] = []

    def write(self, message: str) -> None:
        """Record one step and flush it, so a crash still leaves the trail."""
        self.lines.append(message)
        try:
            self.path.write_text("\n".join(self.lines), encoding="utf-8")
        except OSError:
            pass


def _badge(parent: QWidget) -> QLabel | None:
    """The application icon, when the asset resolves."""
    path = resources.window_icon_path()
    if path is None:
        return None
    pixmap = QPixmap(str(path))
    if pixmap.isNull():
        return None
    label = QLabel(parent)
    label.setPixmap(
        pixmap.scaled(
            BADGE_PX,
            BADGE_PX,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
    )
    return label


class SetupWindow(QWidget):
    """Install or remove Stellody, per user, without administrator rights."""

    def __init__(self, uninstalling: bool) -> None:
        super().__init__()
        self.log = StepLog()
        self.version = read_version()
        self.uninstalling = uninstalling
        self.setWindowTitle(f"{actions.APP_NAME} Setup")
        self.resize(WINDOW_WIDTH_PX, WINDOW_HEIGHT_PX)
        icon_path = resources.application_icon_path()
        if icon_path is not None:
            from PySide6.QtGui import QIcon

            self.setWindowIcon(QIcon(str(icon_path)))
        self.pages = QStackedWidget(self)
        layout = QVBoxLayout(self)
        layout.addWidget(self.pages)
        self._desktop = QCheckBox("Desktop shortcut", self)
        self._start_menu = QCheckBox("Start Menu shortcut", self)
        self._desktop.setChecked(True)
        self._start_menu.setChecked(True)
        self._result = QTextBrowser(self)
        self.pages.addWidget(self._welcome_page())
        self.pages.addWidget(self._result_page())
        self.log.write(f"setup started, version {self.version}")

    def _welcome_page(self) -> QWidget:
        """The first page: what will happen, plus where."""
        page = QWidget(self)
        layout = QVBoxLayout(page)
        badge = _badge(page)
        if badge is not None:
            layout.addWidget(badge, alignment=Qt.AlignmentFlag.AlignHCenter)
        heading = QLabel(f"<h2>{actions.APP_NAME} {self.version}</h2>", page)
        heading.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(heading)
        layout.addWidget(QLabel(self._explanation(), page))
        if not self.uninstalling:
            layout.addWidget(self._desktop)
            layout.addWidget(self._start_menu)
        layout.addStretch()
        layout.addLayout(self._licence_row(page))
        layout.addLayout(self._action_row(page))
        return page

    def _explanation(self) -> str:
        """What this run of the setup program is about to do."""
        target = actions.default_target()
        existing = actions.read_registered()
        if self.uninstalling:
            where = existing.get("InstallLocation", str(target))
            return (
                f"Stellody will be removed from {where}."
                "<br><br>Your music is never touched. Stellody's own library "
                "database is kept, so a later reinstall starts where you left off."
            )
        verb = "reinstalled over" if existing else "installed to"
        return (
            f"Stellody will be {verb}:<br><b>{target}</b><br><br>"
            "Everything is installed for your account only, so Windows will not "
            "ask for administrator rights.<br><br>"
            "Stellody reads your music folder and never writes to it."
        )

    def _licence_row(self, page: QWidget) -> QHBoxLayout:
        """Buttons opening both licences."""
        row = QHBoxLayout()
        model = QPushButton("Model licence (GPL-3.0)", page)
        model.clicked.connect(self._show_model_licence)
        interface = QPushButton("UI licence (LGPL-3.0)", page)
        interface.clicked.connect(self._show_ui_licence)
        row.addWidget(model)
        row.addWidget(interface)
        row.addStretch()
        return row

    def _action_row(self, page: QWidget) -> QHBoxLayout:
        """The trailing Cancel and go-ahead buttons."""
        row = QHBoxLayout()
        row.addStretch()
        cancel = QPushButton("Cancel", page)
        cancel.clicked.connect(self.close)
        row.addWidget(cancel)
        label = "Remove" if self.uninstalling else "Install"
        confirm = QPushButton(label, page)
        confirm.setDefault(True)
        confirm.clicked.connect(self._perform)
        row.addWidget(confirm)
        return row

    def _result_page(self) -> QWidget:
        """The page shown once the work has been done."""
        page = QWidget(self)
        layout = QVBoxLayout(page)
        layout.addWidget(self._result)
        row = QHBoxLayout()
        row.addStretch()
        close = QPushButton("Close", page)
        close.setDefault(True)
        close.clicked.connect(self.close)
        row.addWidget(close)
        layout.addLayout(row)
        return page

    def _show_model_licence(self) -> None:
        """Open the GPL-3.0 text."""
        LicenceDialog(
            "Model licence (GPL-3.0)", resources.model_licence_path(), self
        ).exec()

    def _show_ui_licence(self) -> None:
        """Open the LGPL-3.0 text."""
        LicenceDialog("UI licence (LGPL-3.0)", resources.ui_licence_path(), self).exec()

    def _perform(self) -> None:
        """Do the install or the removal, then report what happened."""
        try:
            message = self._remove() if self.uninstalling else self._install()
        except (OSError, ValueError, RuntimeError) as error:
            self.log.write(f"FAILED: {error}")
            self.log.write(traceback.format_exc())
            message = (
                f"<h3>Setup could not finish</h3><p>{error}</p>"
                f"<p>A step by step log is at {self.log.path}.</p>"
            )
        self._result.setHtml(message)
        self.pages.setCurrentIndex(1)

    def _install(self) -> str:
        """Deploy the application and describe the result."""
        archive = actions.payload_zip()
        if archive is None:
            raise RuntimeError("the setup file does not contain an application payload")
        plan = actions.InstallPlan(
            target=actions.default_target(),
            version=self.version,
            desktop_shortcut=self._desktop.isChecked(),
            start_menu_shortcut=self._start_menu.isChecked(),
        )
        self.log.write(f"installing to {plan.target}")
        executable = actions.install(plan, archive)
        self.log.write(f"installed {executable}")
        return (
            f"<h3>{actions.APP_NAME} {self.version} is installed</h3>"
            f"<p>{executable}</p>"
            "<p>Open it from the Start Menu, then choose your music folder from "
            "the File menu.</p>"
            f"<p>Setup log: {self.log.path}</p>"
        )

    def _remove(self) -> str:
        """Remove the application and describe the result."""
        recorded = actions.read_registered()
        target = pathlib.Path(
            recorded.get("InstallLocation", str(actions.default_target()))
        )
        self.log.write(f"removing {target}")
        actions.uninstall(target)
        self.log.write("removed")
        return (
            f"<h3>{actions.APP_NAME} has been removed</h3>"
            "<p>Your music folder was never touched. Stellody's own library "
            "database has been left in place.</p>"
            f"<p>Setup log: {self.log.path}</p>"
        )


def main(argv: list[str] | None = None) -> int:
    """Run the setup program."""
    arguments = sys.argv if argv is None else argv
    uninstalling = actions.UNINSTALL_FLAG in arguments
    application = QApplication(arguments[:1])
    application.setApplicationName(f"{actions.APP_NAME} Setup")
    application.setStyleSheet(stylesheet(Mode.DARK))
    window = SetupWindow(uninstalling=uninstalling)
    window.show()
    return application.exec()


if __name__ == "__main__":
    sys.exit(main())
