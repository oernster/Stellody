"""The Stellody setup program.

The house shell: a header that never changes, a body showing one screen at a
time and a footer of actions, with a rule between each. The body is centred
rather than packed to the top, so a short screen sits in the middle of the
window instead of leaving a hole above the buttons.

The version is not a chip beside the title. It belongs in the heading of the
screen that is talking about it, which is also where the reference puts it.

The setup program is a Qt application, so it carries ONE licence, the LGPL-3.0
that Qt asks for. Stellody's own split into a model licence and an interface
licence belongs to Stellody, not to the program that installs it.

Every step is written to a log, because the worst installer failures are the
ones that never raise.
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
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from installer import actions, screens, theme, wording
from stellody.shared import resources
from stellody.shared.version import APP_TAGLINE, read_version
from stellody.ui.dialogs import LicenceDialog
from stellody.ui.theme import Mode

LOG_NAME = "stellody-setup.log"
LICENCE_TITLE = "Setup licence (LGPL-3.0)"
TICK = "✓"
ALERT = "⚠"
SCREEN_PROGRESS = 1
SCREEN_VERDICT = 2


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
        self._build_widgets()
        self._build()
        self._apply_theme()
        self.log.write(f"setup started, version {self.version}")

    def _build_widgets(self) -> None:
        """Create every control the screens and the footer share."""
        self._theme_button = QPushButton(self)
        self._theme_button.setObjectName("ThemeToggle")
        self._theme_button.setIconSize(
            QSize(theme.TOGGLE_ICON_PX, theme.TOGGLE_ICON_PX)
        )
        self._theme_button.setToolTip("Switch between light and dark")
        self._desktop = QCheckBox("Create a desktop shortcut", self)
        self._start_menu = QCheckBox("Create a Start Menu entry", self)
        self._sign_in = QCheckBox(f"Start {actions.APP_NAME} when I sign in", self)
        self._minimised = QCheckBox("Start minimised to the notification area", self)
        self._progress = QProgressBar(self)
        self._progress.setRange(0, actions.PCT_DONE)
        self._progress.setValue(0)
        self._progress_title = screens.label(self, "", "Heading")
        self._progress_status = screens.label(self, "", "Status")
        self._verdict_mark = screens.label(self, "", "Verdict")
        self._verdict_title = screens.label(self, "", "Heading")
        self._verdict_lead = screens.label(self, "", "Lead")
        self._primary = QPushButton(self._words(wording.primary_label), self)
        self._primary.setObjectName("Primary")
        self._uninstall = QPushButton("Uninstall", self)
        self._uninstall.setObjectName("Danger")
        self._licence = QPushButton("Licence", self)
        self._close = QPushButton("Close", self)
        self._shown = False
        self._start = QWidget(self)
        self._start.setFixedSize(0, 0)
        self._start.setFocusPolicy(Qt.FocusPolicy.TabFocus)

    # ------------------------------------------------------------- behaviour

    def showEvent(self, event) -> None:
        """Start neutral, so no control wears a ring until one is asked for."""
        super().showEvent(event)
        if not self._shown:
            self._shown = True
            self._start.setFocus()

    def keyPressEvent(self, event) -> None:
        """Enter activates the focused control, as Space already does."""
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            target = self.focusWidget()
            if isinstance(target, QAbstractButton) and target.isEnabled():
                target.click()
                return
        super().keyPressEvent(event)

    # ----------------------------------------------------------------- shell

    def _build(self) -> None:
        """Header, a rule, the centred body, a rule, then the footer."""
        shell = QVBoxLayout(self)
        shell.setContentsMargins(
            theme.SHELL_MARGIN_SIDE_PX,
            theme.SHELL_MARGIN_TOP_PX,
            theme.SHELL_MARGIN_SIDE_PX,
            theme.SHELL_MARGIN_BOTTOM_PX,
        )
        shell.setSpacing(theme.HEADER_PAD_PX)
        shell.addLayout(self._header())
        shell.addWidget(screens.rule(self))
        self._body = QStackedWidget(self)
        self._body.addWidget(self._choices_screen())
        self._body.addWidget(
            screens.progress(
                self, self._progress_title, self._progress, self._progress_status
            )
        )
        self._body.addWidget(
            screens.verdict(
                self, self._verdict_mark, self._verdict_title, self._verdict_lead
            )
        )
        shell.addWidget(self._body, 1)
        shell.addWidget(screens.rule(self))
        shell.addLayout(self._footer())

    def _header(self) -> QHBoxLayout:
        """The identity, drawn at a size that can be read across the room."""
        row = QHBoxLayout()
        row.setSpacing(theme.HEADER_GAP_PX)
        icon_path = resources.window_icon_path()
        if icon_path is not None:
            mark = QLabel(self)
            mark.setPixmap(
                QIcon(str(icon_path)).pixmap(QSize(theme.MARK_PX, theme.MARK_PX))
            )
            mark.setFixedSize(theme.MARK_PX, theme.MARK_PX)
            row.addWidget(mark, alignment=Qt.AlignmentFlag.AlignVCenter)
        who = QVBoxLayout()
        who.setSpacing(0)
        who.addWidget(screens.label(self, f"{actions.APP_NAME} Setup", "HeaderTitle"))
        who.addWidget(screens.label(self, APP_TAGLINE, "HeaderSub"))
        row.addLayout(who, 1)
        self._theme_button.clicked.connect(self._toggle_theme)
        row.addWidget(self._theme_button, alignment=Qt.AlignmentFlag.AlignVCenter)
        return row

    def _footer(self) -> QHBoxLayout:
        """The actions, right aligned, under a rule."""
        row = QHBoxLayout()
        row.setSpacing(theme.FOOTER_GAP_PX)
        row.addStretch()
        self._licence.clicked.connect(self._show_licence)
        row.addWidget(self._licence)
        self._uninstall.clicked.connect(self._remove)
        self._uninstall.setVisible(bool(self.installed) and not self.uninstalling)
        row.addWidget(self._uninstall)
        self._close.clicked.connect(self.close)
        row.addWidget(self._close)
        self._primary.clicked.connect(self._perform)
        row.addWidget(self._primary)
        return row

    # --------------------------------------------------------------- screens

    def _choices_screen(self) -> QWidget:
        """The opening screen, with the options only when installing."""
        if self.uninstalling:
            return screens.choices(
                self, self._words(wording.heading), self._words(wording.lead), "", ()
            )
        self._desktop.setChecked(True)
        self._start_menu.setChecked(True)
        self._sign_in.toggled.connect(self._minimised.setEnabled)
        self._minimised.setEnabled(False)
        options = (
            (self._desktop, ""),
            (self._start_menu, ""),
            (
                self._sign_in,
                (
                    f"{actions.APP_NAME} opens with Windows instead of "
                    "waiting to be asked."
                ),
            ),
            (
                self._minimised,
                "It waits quietly in the notification area until you open it.",
            ),
        )
        return screens.choices(
            self,
            self._words(wording.heading),
            self._words(wording.lead),
            str(actions.default_target()),
            options,
        )

    def _words(self, decide) -> str:
        """Ask the wording module about the state this run is in."""
        return decide(self.installed, self.version, self.uninstalling)

    # --------------------------------------------------------------- actions

    def _apply_theme(self) -> None:
        """Repaint everything in the current appearance."""
        arriving = theme.next_mode(self.mode)
        icon_path = (
            resources.light_mode_icon_path()
            if arriving is Mode.LIGHT
            else resources.dark_mode_icon_path()
        )
        if icon_path is not None:
            self._theme_button.setIcon(QIcon(str(icon_path)))
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

    def _report(self, percent: int, message: str) -> None:
        """Move the bar and say which step is running."""
        self._progress.setValue(percent)
        self._progress_status.setText(message)
        QApplication.processEvents()

    def _working(self, title: str) -> None:
        """Show the progress screen, with the actions withheld while it runs."""
        self._progress_title.setText(title)
        self._progress.setValue(0)
        self._progress_status.setText("Starting...")
        self._body.setCurrentIndex(SCREEN_PROGRESS)
        for button in (self._primary, self._uninstall):
            button.setVisible(False)
        QApplication.processEvents()

    def _verdict(self, mark: str, title: str, lead: str) -> None:
        """Show how it ended, leaving only the licence and Close."""
        self._verdict_mark.setText(mark)
        self._verdict_title.setText(title)
        self._verdict_lead.setText(lead)
        self._body.setCurrentIndex(SCREEN_VERDICT)

    def _perform(self) -> None:
        """Run the go-ahead action, then say how it ended."""
        if self.uninstalling:
            self._remove()
            return
        self._working(f"Installing {actions.APP_NAME} {self.version}")
        try:
            where = self._install()
        except (OSError, ValueError, RuntimeError) as error:
            self.log.write(f"FAILED: {error}")
            self.log.write(traceback.format_exc())
            self._verdict(
                ALERT,
                "Setup could not finish",
                f"{error}. A step by step log is at {self.log.path}.",
            )
            return
        self._verdict(
            TICK,
            f"{actions.APP_NAME} {self.version} is installed",
            f"It is at {where}. Open it from the Start Menu, then choose your "
            "music folder from the File menu.",
        )

    def _install(self) -> pathlib.Path:
        """Deploy the application, reporting each step as it goes."""
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
        executable = actions.install(plan, archive, self._report)
        self.log.write(f"installed {executable}")
        return executable.parent

    def _remove(self) -> None:
        """Remove the application, then say how it ended."""
        recorded = actions.read_registered()
        target = pathlib.Path(
            recorded.get("InstallLocation", str(actions.default_target()))
        )
        self._working(f"Removing {actions.APP_NAME}")
        try:
            actions.uninstall(target, self._report)
        except OSError as error:
            self.log.write(f"FAILED: {error}")
            self._verdict(ALERT, "Setup could not finish", str(error))
            return
        self.log.write("removed")
        self._verdict(
            TICK,
            f"{actions.APP_NAME} has been removed",
            "Your music was never touched; the library database has been left "
            "in place.",
        )


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
