"""Doing the work, then saying honestly how it went.

Split from the window's shell because the two answer different questions: over
there is what setup looks like on each route, here is what pressing the
go-ahead actually does. Every path through this module ends in one of two
places, a verdict on screen or the application running, so setup can never
finish by quietly doing nothing.

Nothing here reaches for a control it was not given by the window it is mixed
into; the window owns the state and this owns the sequence.
"""

from __future__ import annotations

import pathlib
import time
import traceback

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from installer import actions, launching, running, screens, wording
from installer.footer import PRIMARY, Action
from installer.plan import InstallPlan
from installer.route import Route

TICK = "✓"
ALERT = "⚠"
FAILED_HEADING = "Setup could not finish"


class Performing:
    """The work half of the setup window, mixed into it."""

    # ------------------------------------------------------------- reporting

    def _report(self, percent: int, message: str) -> None:
        """Move the bar and say which step is running."""
        self._progress.setValue(percent)
        self._progress_status.setText(message)
        QApplication.processEvents()

    def _working(self, title: str) -> None:
        """Show the progress screen, with no actions offered while it runs."""
        self._progress_title.setText(title)
        self._progress.setValue(0)
        self._progress_status.setText("Starting...")
        self._footer.show_actions(())
        self._body.setCurrentIndex(screens.SCREEN_PROGRESS)
        QApplication.processEvents()

    def _verdict(self, mark: str, title: str, lead: str) -> None:
        """Show how it ended, with nothing left to do but close."""
        self._verdict_mark.setText(mark)
        self._verdict_title.setText(title)
        self._verdict_lead.setText(lead)
        self._body.setCurrentIndex(screens.SCREEN_VERDICT)
        self._footer.show_actions((Action("Close", self.close, PRIMARY),))

    def _failed(self, error: Exception) -> None:
        """Report a step that raised, naming where its trail is written."""
        self.log.write(f"FAILED: {error}")
        self.log.write(traceback.format_exc())
        self._verdict(
            ALERT, FAILED_HEADING, f"{error}. A step by step log is at {self.log.path}."
        )

    # --------------------------------------------------------------- guarding

    def _guarded(self, work) -> None:
        """Run the work once nothing is holding the application's files open.

        Extracting over a locked executable raises partway through, so this is
        asked BEFORE any file is touched rather than discovered halfway.
        """
        if not running.is_running():
            work()
            return
        self.log.write("the application is running")
        self._body.setCurrentIndex(screens.SCREEN_RUNNING)
        self._footer.show_actions(
            (
                Action("Cancel", self._show_current),
                Action(
                    "Close it and continue",
                    lambda: self._close_then(work),
                    PRIMARY,
                ),
            )
        )

    def _close_then(self, work) -> None:
        """Close the running application, then carry on with what was asked."""
        self._working(f"Closing {actions.APP_NAME}")
        self._report(actions.PCT_START, "Waiting for it to close...")
        if not running.close():
            self._verdict(
                ALERT,
                f"{actions.APP_NAME} is still open",
                wording.STILL_RUNNING_LEAD,
            )
            return
        self.log.write("the application was closed")
        work()

    # ------------------------------------------------------------------ work

    def _target(self) -> pathlib.Path:
        """Where the application lives: the recorded install, else the default."""
        if self.here.installed:
            return self.here.location
        return actions.default_target()

    def _plan(self) -> InstallPlan:
        """What this run of the boxes asks an install to do."""
        return InstallPlan(
            target=self._target(),
            version=self.version,
            desktop_shortcut=self._desktop.isChecked(),
            start_menu_shortcut=self._start_menu.isChecked(),
            start_on_sign_in=self._sign_in.isChecked(),
        )

    def _archive(self) -> pathlib.Path:
        """The bundled application payload; absent means setup is incomplete."""
        archive = actions.payload_zip()
        if archive is None:
            raise RuntimeError("the setup file does not contain an application payload")
        return archive

    def _write_files(self, reinstalling: bool = False) -> None:
        """Install or reinstall, then finish however the launch box asked."""
        titles = {
            Route.INSTALL: f"Installing {actions.APP_NAME} {self.version}",
            Route.UPDATE: f"Updating {actions.APP_NAME}",
            Route.DOWNGRADE: "Going back a version",
            Route.MANAGE: f"Reinstalling {actions.APP_NAME}",
        }
        self._working(titles[Route.MANAGE if reinstalling else self.route])
        try:
            plan = self._plan()
            self.log.write(f"installing to {plan.target}")
            executable = actions.install(
                plan,
                self._archive(),
                self._report,
                anew=reinstalling or self.route is Route.INSTALL,
            )
        except (OSError, ValueError, RuntimeError) as error:
            self._failed(error)
            return
        self.log.write(f"installed {executable}")
        if reinstalling:
            self._finish(
                executable,
                f"{actions.APP_NAME} is reinstalled",
                wording.REINSTALLED_LEAD,
            )
            return
        self._finish(
            executable,
            f"{actions.APP_NAME} {self.version} is installed",
            f"It is at {executable.parent}. Open it from the Start Menu, then "
            "choose your music folder from the File menu.",
        )

    def _repair(self) -> None:
        """Put the files back, leaving every other choice as it stands."""
        self._working(f"Repairing {actions.APP_NAME}")
        try:
            executable = actions.repair(self._target(), self._archive(), self._report)
        except (OSError, ValueError, RuntimeError) as error:
            self._failed(error)
            return
        self.log.write("repaired")
        self._finish(executable, "Repair complete", wording.REPAIRED_LEAD)

    def _remove(self) -> None:
        """Remove the application, then say what was and was not taken."""
        forgetting = self._forget.isChecked()
        self._working(f"Removing {actions.APP_NAME}")
        try:
            actions.uninstall(self._target(), self._report, remove_data=forgetting)
        except OSError as error:
            self._failed(error)
            return
        self.log.write(f"removed, library index removed: {forgetting}")
        self._verdict(
            TICK,
            f"{actions.APP_NAME} has been removed",
            wording.REMOVED_LIBRARY_LEAD if forgetting else wording.KEPT_LIBRARY_LEAD,
        )

    # ---------------------------------------------------------------- finish

    def _finish(self, executable: pathlib.Path, title: str, lead: str) -> None:
        """Show the verdict, then start the application if that was asked."""
        wanted = self._launch.isChecked()
        if not wanted:
            self._verdict(TICK, title, lead)
            return
        process = launching.launch(executable)
        if process is None:
            self.log.write("could not start it")
            self._verdict(TICK, title, f"{lead} Setup could not start it, though.")
            return
        self._verdict(TICK, title, f"{lead} {wording.LAUNCHING_LEAD}")
        self._front_pid = process.pid
        self._front_deadline = time.monotonic() + launching.FOREGROUND_WAIT_S
        self._front_timer = QTimer(self)
        self._front_timer.timeout.connect(self._front_then_close)
        self._front_timer.start(launching.FOREGROUND_POLL_MS)

    def _front_then_close(self) -> None:
        """Wait for the new window, bring it forward, then leave.

        Closing first would hand the foreground back to whatever was behind
        setup; the window arriving afterwards would then only flash on the
        taskbar. The wait is bounded, so a window that never comes still
        closes setup rather than leaving it running.

        The deadline is read BEFORE the window is looked for; the two are
        short circuited. Looking for a window is a walk through the system's
        own tables; if that ever raises, the exception ends this slot in
        silence and the timer goes on firing into it forever, which is a setup
        program that never leaves. Once the deadline is past, nothing is
        called that could keep it here.
        """
        expired = time.monotonic() > self._front_deadline
        if expired or launching.front(self._front_pid):
            self._front_timer.stop()
            self.close()
