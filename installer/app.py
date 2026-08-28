"""The Stellody setup program.

One window in the house shape: a header carrying the icon, the name and the
version, with the appearance toggle and the licence at its right; then what is
already installed, where this will go and the choices; then the action row.
There is no second page, because a result belongs on the status line where the
user is already looking.

The setup program is a Qt application, so it carries ONE licence, the LGPL-3.0
that Qt asks for. The two licence split belongs to Stellody itself, not to the
program that installs it.

Every step is written to a log beside the install, because the worst installer
failures are the ones that never raise.
"""

from __future__ import annotations

import pathlib
import sys
import tempfile
import traceback

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QAbstractButton,
    QApplication,
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from installer import actions, theme
from stellody.shared import resources
from stellody.shared.version import APP_TAGLINE, read_version
from stellody.ui.dialogs import LicenceDialog
from stellody.ui.theme import Mode

LOG_NAME = "stellody-setup.log"
LICENCE_LABEL = "Licence"
LICENCE_TITLE = "Setup licence (LGPL-3.0)"


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


def _neutral_start(parent: QWidget) -> QWidget:
    """A zero size focus sink, so launch highlights nothing at all."""
    sink = QWidget(parent)
    sink.setFixedSize(0, 0)
    sink.setFocusPolicy(Qt.FocusPolicy.TabFocus)
    return sink


class SetupWindow(QWidget):
    """Install or remove Stellody, per user, without administrator rights."""

    def __init__(self, uninstalling: bool) -> None:
        super().__init__()
        self.log = StepLog()
        self.version = read_version()
        self.installed = actions.installed_version()
        self.uninstalling = uninstalling
        self.mode = Mode.DARK
        self.setWindowTitle(f"{actions.APP_NAME} Setup")
        self.resize(theme.WINDOW_WIDTH_PX, theme.WINDOW_HEIGHT_PX)
        icon_path = resources.application_icon_path()
        if icon_path is not None:
            self.setWindowIcon(QIcon(str(icon_path)))
        self._desktop = QCheckBox("Create a desktop shortcut", self)
        self._start_menu = QCheckBox("Create a Start Menu shortcut", self)
        self._sign_in = QCheckBox(
            f"Start {actions.APP_NAME} when I sign in to Windows", self
        )
        self._minimised = QCheckBox("Start minimised to the system tray", self)
        self._status = QLabel("", self)
        self._status.setObjectName("StatusLine")
        self._status.setWordWrap(True)
        self._theme_button = QPushButton("", self)
        self._theme_button.setObjectName("ThemeToggle")
        self._primary = QPushButton(self._primary_label(), self)
        self._primary.setObjectName("PrimaryAction")
        self._uninstall = QPushButton("Uninstall", self)
        self._uninstall.setObjectName("DangerAction")
        self._shown = False
        self._start = _neutral_start(self)
        self._build()
        self._apply_theme()
        self.log.write(f"setup started, version {self.version}")

    # ------------------------------------------------------------- behaviour

    def showEvent(self, event) -> None:
        """Start neutral, so no control wears a ring until one is asked for."""
        super().showEvent(event)
        if not self._shown:
            self._shown = True
            self._start.setFocus()

    def keyPressEvent(self, event) -> None:
        """Enter activates the focused control, as Space already does.

        A plain QWidget window has no dialog default button, so without this a
        keyboard user reaches Install then finds Enter does nothing.
        """
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            target = self.focusWidget()
            if isinstance(target, QAbstractButton) and target.isEnabled():
                target.click()
                return
        super().keyPressEvent(event)

    # ----------------------------------------------------------------- layout

    def _build(self) -> None:
        """Assemble the whole window as one top-to-bottom column."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(
            theme.MARGIN_SIDE_PX,
            theme.MARGIN_TOP_PX,
            theme.MARGIN_SIDE_PX,
            theme.MARGIN_BOTTOM_PX,
        )
        layout.setSpacing(theme.SECTION_SPACING_PX)
        layout.addLayout(self._header())

        subtitle = QLabel(self._subtitle(), self)
        subtitle.setObjectName("SubTitle")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(subtitle)

        tagline = QLabel(APP_TAGLINE, self)
        tagline.setObjectName("Tagline")
        tagline.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        tagline.setWordWrap(True)
        layout.addWidget(tagline)

        divider = QFrame(self)
        divider.setObjectName("Divider")
        divider.setFixedHeight(theme.DIVIDER_PX)
        layout.addWidget(divider)

        state = QLabel(self._state_line(), self)
        state.setObjectName("InstallPath")
        state.setWordWrap(True)
        layout.addWidget(state)

        location = QLabel(f"Install location: {actions.default_target()}", self)
        location.setObjectName("InstallPath")
        location.setWordWrap(True)
        layout.addWidget(location)

        for box in self._choices():
            layout.addWidget(box)
        layout.addWidget(self._status)
        layout.addStretch()
        layout.addLayout(self._action_row())

    def _header(self) -> QHBoxLayout:
        """Icon, name and version on the left; appearance and licence right."""
        row = QHBoxLayout()
        row.setSpacing(theme.HEADER_SPACING_PX)
        icon_path = resources.window_icon_path()
        if icon_path is not None:
            badge = QLabel(self)
            badge.setPixmap(
                QIcon(str(icon_path)).pixmap(QSize(theme.ICON_PX, theme.ICON_PX))
            )
            row.addWidget(badge)
        title = QLabel(f"{actions.APP_NAME} Setup", self)
        title.setObjectName("HeaderTitle")
        row.addWidget(title)
        version = QLabel(f"v{self.version}", self)
        version.setObjectName("HeaderVersion")
        version.setAlignment(Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignLeft)
        row.addWidget(version)
        row.addStretch()
        self._theme_button.clicked.connect(self._toggle_theme)
        row.addWidget(self._theme_button)
        licence = QPushButton(LICENCE_LABEL, self)
        licence.setObjectName("LicenceButton")
        licence.clicked.connect(self._show_licence)
        row.addWidget(licence)
        return row

    def _choices(self) -> tuple[QCheckBox, ...]:
        """The install options, wired so an unavailable one cannot mislead."""
        if self.uninstalling:
            return ()
        self._desktop.setChecked(True)
        self._start_menu.setChecked(True)
        self._sign_in.toggled.connect(self._minimised.setEnabled)
        self._minimised.setEnabled(self._sign_in.isChecked())
        return (self._desktop, self._start_menu, self._sign_in, self._minimised)

    def _action_row(self) -> QHBoxLayout:
        """Uninstall on the left, then the go-ahead and Close on the right."""
        row = QHBoxLayout()
        row.setSpacing(theme.BUTTON_GAP_PX)
        self._uninstall.setVisible(bool(self.installed) and not self.uninstalling)
        self._uninstall.clicked.connect(self._remove)
        row.addWidget(self._uninstall)
        row.addStretch()
        self._primary.clicked.connect(self._perform)
        row.addWidget(self._primary)
        close = QPushButton("Close", self)
        close.setObjectName("SecondaryAction")
        close.clicked.connect(self.close)
        row.addWidget(close)
        return row

    # ------------------------------------------------------------------ words

    def _primary_label(self) -> str:
        """What the go-ahead button does, given what is already installed."""
        if self.uninstalling:
            return "Uninstall"
        if not self.installed:
            return "Install"
        here = actions.version_key(self.installed)
        arriving = actions.version_key(self.version)
        if here == arriving:
            return "Reinstall"
        return "Update" if here < arriving else "Reinstall (older)"

    def _subtitle(self) -> str:
        """The centred line naming what this run of setup is for."""
        if self.uninstalling:
            return f"Remove {actions.APP_NAME}"
        if not self.installed:
            return f"Welcome to the {actions.APP_NAME} installer"
        return f"{actions.APP_NAME} is already installed"

    def _state_line(self) -> str:
        """What is installed now, so the version is never left implicit."""
        if self.uninstalling:
            installed = self.installed or self.version
            return f"Version {installed} is installed on this account."
        return actions.upgrade_summary(self.installed, self.version)

    # --------------------------------------------------------------- actions

    def _apply_theme(self) -> None:
        """Repaint everything in the current appearance."""
        self._theme_button.setText(theme.next_mode(self.mode).value.title())
        application = QApplication.instance()
        if application is not None:
            application.setStyleSheet(theme.installer_stylesheet(self.mode))

    def _toggle_theme(self) -> None:
        """Switch between the light and dark palettes."""
        self.mode = theme.next_mode(self.mode)
        self._apply_theme()

    def _show_licence(self) -> None:
        """Open the LGPL-3.0 text the setup program itself is covered by."""
        LicenceDialog(LICENCE_TITLE, resources.ui_licence_path(), self).exec()

    def _busy(self, message: str) -> None:
        """Say what is happening, with the actions held while it happens."""
        self._status.setText(message)
        self._primary.setEnabled(False)
        self._uninstall.setEnabled(False)
        QApplication.processEvents()

    def _released(self) -> None:
        """Give the actions back once the work has finished."""
        self._primary.setEnabled(True)
        self._uninstall.setEnabled(True)

    def _perform(self) -> None:
        """Run the go-ahead action, reporting the outcome on the status line."""
        if self.uninstalling:
            self._remove()
            return
        self._busy("Installing...")
        try:
            self._status.setText(self._install())
        except (OSError, ValueError, RuntimeError) as error:
            self.log.write(f"FAILED: {error}")
            self.log.write(traceback.format_exc())
            self._status.setText(
                f"Setup could not finish: {error}. Log: {self.log.path}"
            )
        self._released()

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
            start_on_sign_in=self._sign_in.isChecked(),
            start_minimised=self._sign_in.isChecked() and self._minimised.isChecked(),
        )
        self.log.write(f"installing to {plan.target}")
        executable = actions.install(plan, archive)
        self.log.write(f"installed {executable}")
        self.installed = self.version
        self._primary.setText(self._primary_label())
        self._uninstall.setVisible(True)
        return f"{actions.APP_NAME} {self.version} is installed at {executable.parent}."

    def _remove(self) -> None:
        """Remove the application, reporting the outcome on the status line."""
        recorded = actions.read_registered()
        target = pathlib.Path(
            recorded.get("InstallLocation", str(actions.default_target()))
        )
        self._busy("Removing...")
        try:
            actions.uninstall(target)
        except OSError as error:
            self.log.write(f"FAILED: {error}")
            self._status.setText(f"Setup could not remove Stellody: {error}")
            self._released()
            return
        self.log.write("removed")
        self.installed = ""
        self._primary.setText(self._primary_label())
        self._uninstall.setVisible(False)
        self._status.setText(
            f"{actions.APP_NAME} has been removed. Your music was never touched "
            "and its library database has been left in place."
        )
        self._released()


def main(argv: list[str] | None = None) -> int:
    """Run the setup program."""
    arguments = sys.argv if argv is None else argv
    uninstalling = actions.UNINSTALL_FLAG in arguments
    application = QApplication(arguments[:1])
    application.setApplicationName(f"{actions.APP_NAME} Setup")
    window = SetupWindow(uninstalling=uninstalling)
    window.show()
    return application.exec()


if __name__ == "__main__":
    sys.exit(main())
