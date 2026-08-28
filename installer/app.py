"""The Stellody setup program.

The house shell: a header that never changes, a body showing one screen at a
time and a footer of actions, with a rule between each. The body is centred
rather than packed to the top, so a short screen sits in the middle of the
window instead of leaving a hole above the buttons.

What setup is FOR is decided once, from what the machine already holds: a first
install, an update, a downgrade, a matching version to manage or a removal.
That reading picks the screen, its heading, the versions it shows and the
actions under it, so no two of those can contradict each other.

The footer belongs to the screen rather than to the window. A screen with
nothing safe to offer, the one that is working, offers nothing at all.

Every step is written to a log, because the worst installer failures are the
ones that never raise.
"""

from __future__ import annotations

import sys

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QAbstractButton,
    QApplication,
    QCheckBox,
    QProgressBar,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from installer import (
    actions,
    appearance,
    existing,
    registry,
    screens,
    shell,
    theme,
    wording,
)
from installer.footer import DANGER, PRIMARY, Action, Footer
from installer.performing import Performing
from installer.route import Route, route_for
from installer.steplog import StepLog
from stellody.shared import resources
from stellody.shared.version import APP_TAGLINE, read_version
from stellody.ui.dialogs import LicenceDialog
from stellody.ui.theme import Mode

LICENCE_TITLE = "Setup licence (LGPL-3.0)"


class SetupWindow(Performing, QWidget):
    """Install, repair or remove Stellody, per user, without admin rights.

    The setup program is a Qt application, so it carries ONE licence, the
    LGPL-3.0 that Qt asks for. Stellody's own split into a model licence and an
    interface licence belongs to Stellody, not to the program that installs it.
    """

    def __init__(self, uninstalling: bool) -> None:
        super().__init__()
        self.log = StepLog()
        self.version = read_version()
        self.here = existing.look()
        # The route never becomes UNINSTALL: removal is a screen reachable from
        # every other one, so the screen behind it stays the one to come back to.
        self.route = route_for(self.here.version, self.version, uninstalling=False)
        self._uninstalling = uninstalling
        self.mode = Mode.DARK
        self.setObjectName("Shell")
        self.setWindowTitle(f"{actions.APP_NAME} Setup")
        self.resize(theme.WINDOW_WIDTH_PX, theme.WINDOW_HEIGHT_PX)
        icon_path = resources.application_icon_path()
        if icon_path is not None:
            self.setWindowIcon(QIcon(str(icon_path)))
        self._build_widgets()
        self._build()
        self._apply_theme()
        self._show_current()
        self.log.write(f"setup started, version {self.version}, {self.route.value}")

    # --------------------------------------------------------------- controls

    def _build_widgets(self) -> None:
        """Create every control the screens and the footer share."""
        self._theme_button = QPushButton(self)
        self._theme_button.setObjectName("ThemeToggle")
        self._theme_button.setIconSize(
            QSize(theme.TOGGLE_ICON_PX, theme.TOGGLE_ICON_PX)
        )
        self._theme_button.setToolTip("Switch between light and dark")
        self._licence = QPushButton("Licence", self)
        self._desktop = QCheckBox(wording.DESKTOP_LABEL, self)
        self._start_menu = QCheckBox(wording.START_MENU_LABEL, self)
        self._sign_in = QCheckBox(wording.SIGN_IN_LABEL, self)
        self._launch = QCheckBox(wording.LAUNCH_LABEL, self)
        self._forget = QCheckBox(wording.FORGET_LABEL, self)
        self._progress = QProgressBar(self)
        self._progress.setRange(0, actions.PCT_DONE)
        self._progress.setValue(0)
        self._progress_title = shell.label(self, "", "Heading")
        self._progress_status = shell.label(self, "", "Status")
        self._verdict_mark = shell.label(self, "", "Verdict")
        self._verdict_title = shell.label(self, "", "Heading")
        self._verdict_lead = shell.label(self, "", "Lead")
        self._footer = Footer(self)
        self._shown = False
        self._start = QWidget(self)
        self._start.setFixedSize(0, 0)
        self._start.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        self._set_choices()

    def _set_choices(self) -> None:
        """Open every box on what is already true, then act on any change.

        A box that says what is there is the whole point of reading the machine
        first: setup used to offer a shortcut the user had deliberately deleted
        as though they had asked for it back.
        """
        fresh = not self.here.installed
        self._desktop.setChecked(True if fresh else self.here.desktop)
        self._start_menu.setChecked(True if fresh else self.here.start_menu)
        self._sign_in.setChecked(self.here.sign_in)
        self._launch.setChecked(True)
        if self.route is not Route.MANAGE:
            return
        # On a matching version there is nothing to install, so a box that only
        # took effect on a go-ahead would never take effect at all.
        for box in (self._desktop, self._start_menu):
            box.toggled.connect(self._apply_shortcuts)
        self._sign_in.toggled.connect(self._apply_sign_in)

    def _apply_shortcuts(self) -> None:
        """Put the shortcuts where the boxes now say they should be."""
        actions.set_shortcuts(
            self.here.executable,
            self._desktop.isChecked(),
            self._start_menu.isChecked(),
        )
        self.log.write("shortcuts applied")

    def _apply_sign_in(self) -> None:
        """Record how it should start, the moment the choice is made."""
        registry.write_sign_in_entry(self.here.executable, self._sign_in.isChecked())
        self.log.write("sign-in entry applied")

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
        layout = QVBoxLayout(self)
        layout.setContentsMargins(
            theme.SHELL_MARGIN_SIDE_PX,
            theme.SHELL_MARGIN_TOP_PX,
            theme.SHELL_MARGIN_SIDE_PX,
            theme.SHELL_MARGIN_BOTTOM_PX,
        )
        layout.setSpacing(theme.HEADER_PAD_PX)
        layout.addLayout(
            shell.header(
                self,
                f"{actions.APP_NAME} Setup",
                APP_TAGLINE,
                resources.window_icon_path(),
                (self._licence, self._theme_button),
            )
        )
        layout.addWidget(shell.rule(self))
        self._body = QStackedWidget(self)
        self._body.setObjectName("Body")
        for screen in self._screens():
            self._body.addWidget(screen)
        layout.addWidget(self._body, 1)
        layout.addWidget(shell.rule(self))
        layout.addWidget(self._footer)
        self._licence.clicked.connect(self._show_licence)
        self._theme_button.clicked.connect(self._toggle_theme)

    def _screens(self) -> tuple[QWidget, ...]:
        """Every screen, in the order the stack indices name them."""
        return (
            self._route_screen(),
            self._uninstall_screen(),
            screens.message(self, wording.RUNNING_HEADING, wording.RUNNING_LEAD),
            screens.progress(
                self, self._progress_title, self._progress, self._progress_status
            ),
            screens.verdict(
                self, self._verdict_mark, self._verdict_title, self._verdict_lead
            ),
        )

    def _route_screen(self) -> QWidget:
        """What this run is for, with the choices that shape it."""
        options = (
            (self._start_menu, wording.START_MENU_HINT),
            (self._desktop, ""),
            (self._sign_in, wording.SIGN_IN_HINT),
            (self._launch, ""),
        )
        location = str(self._target()) if self.route is Route.INSTALL else ""
        versions = None
        if self.route in (Route.UPDATE, Route.DOWNGRADE):
            versions = (f"v{self.here.version}", f"v{self.version}")
        return screens.choices(
            self,
            wording.heading(self.route, self.here.version, self.version),
            wording.lead(self.route),
            options,
            location,
            versions,
        )

    def _uninstall_screen(self) -> QWidget:
        """The removal screen, reachable from every other one."""
        return screens.choices(
            self,
            wording.heading(Route.UNINSTALL, self.here.version, self.version),
            wording.lead(Route.UNINSTALL),
            ((self._forget, wording.FORGET_HINT),),
        )

    # --------------------------------------------------------------- routing

    def _show_current(self) -> None:
        """Show whichever screen is due, after a start or an interruption."""
        if self._uninstalling:
            self._show_uninstall()
            return
        self._show_route()

    def _show_route(self) -> None:
        """The screen this run is for, with the actions that belong to it."""
        self._uninstalling = False
        self._body.setCurrentIndex(screens.SCREEN_ROUTE)
        self._footer.show_actions(self._route_actions())

    def _route_actions(self) -> tuple[Action, ...]:
        """The actions under the route screen, destructive ones marked."""
        go = Action(wording.primary_label(self.route), self._go, PRIMARY)
        if self.route is Route.INSTALL:
            return (Action("Cancel", self.close), go)
        remove = Action("Uninstall", self._show_uninstall, DANGER)
        if self.route is Route.MANAGE:
            return (
                remove,
                Action("Close", self.close),
                Action("Reinstall", self._reinstall),
                go,
            )
        return (remove, Action("Not now", self.close), go)

    def _show_uninstall(self) -> None:
        """Ask before removing anything, with the one extra choice removal has."""
        self._uninstalling = True
        self._body.setCurrentIndex(screens.SCREEN_UNINSTALL)
        self._footer.show_actions(
            (
                Action("Cancel", self._cancel_removal),
                Action("Uninstall", lambda: self._guarded(self._remove), DANGER),
            )
        )

    def _cancel_removal(self) -> None:
        """Back to what setup was otherwise for; nothing, when it was only this."""
        if self.here.installed:
            self._show_route()
            return
        self.close()

    def _go(self) -> None:
        """The go-ahead: a repair when the version already matches, else files."""
        if self.route is Route.MANAGE:
            self._guarded(self._repair)
            return
        self._guarded(self._write_files)

    def _reinstall(self) -> None:
        """Write the files again with the choices showing on screen."""
        self._guarded(lambda: self._write_files(reinstalling=True))

    # --------------------------------------------------------------- actions

    def _apply_theme(self) -> None:
        """Repaint everything in the current appearance."""
        appearance.apply(self.mode, self._theme_button)

    def _toggle_theme(self) -> None:
        """Switch between the light and dark palettes."""
        self.mode = theme.next_mode(self.mode)
        self._apply_theme()

    def _show_licence(self) -> None:
        """Open the LGPL-3.0 text the setup program itself is covered by."""
        LicenceDialog(LICENCE_TITLE, resources.ui_licence_path(), self).exec()


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
