"""How the window comes and goes: the tray, the close button and the exit.

Split from the window for the same reason the scanning and the playing are:
over there is what the window IS, here is what happens when somebody tries to
put it away. It is one concern rather than three. The cross, the tray and
Quit are three doors into the same decision; having them apart is how one of
them came to end differently from the others.

Stellody does not end when its last window closes. That is deliberate: it is
what lets the cross leave the application running in the notification area. The
price is that nothing here may assume Qt will do the leaving; ending the
application is said out loud, on every path that means it.
"""

from __future__ import annotations

from PySide6.QtCore import Slot
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import QApplication

from stellody.ui.close_prompt import CloseAction, ClosePrompt
from stellody.ui.settings_keys import SETTING_CLOSE


class Leaving:
    """The coming and going half of the window."""

    @Slot()
    def quit_application(self) -> None:
        """Leave, whatever the close button is set to do."""
        self._note("quit asked for; closing the window to get there")
        self._quitting = True
        self.close()

    def closeEvent(self, event: QCloseEvent) -> None:
        """Honour the stored close behaviour, asking when none is stored."""
        if self._quitting or not self._notification.isVisible():
            self._note(
                f"closing for good: quitting={self._quitting} "
                f"tray={self._notification.isVisible()}"
            )
            self._leave_for_good(event)
            return
        action = self._settings.get_setting(SETTING_CLOSE, CloseAction.ASK.value)
        if action == CloseAction.ASK.value:
            action = self._ask_close_action()
        self._note(f"the close button means: {action}")
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
        self._note("stopping the transport timer")
        self._transport_timer.stop()
        self._note("stopping the transport")
        self._transport.stop()
        self._note("waiting for the scan runner")
        self._runner.wait()
        self._note("scan runner done; accepting the close")
        event.accept()
        self._note("calling the departure")
        depart = self._leave or QApplication.quit
        depart()
        self._note("the departure returned; the event loop should now end")

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
        """Bring the window back, when nobody said what asked for it."""
        self._restore("an unnamed request")

    @Slot()
    def restore_for_channel(self) -> None:
        """A later launch asked, over the activation channel."""
        self._restore("another launch asked over the channel")

    @Slot()
    def restore_for_tray_icon(self) -> None:
        """Somebody clicked the icon in the notification area."""
        self._restore("the tray icon was clicked")

    @Slot()
    def restore_for_tray_menu(self) -> None:
        """Somebody chose Show on the notification area's menu."""
        self._restore("Show was chosen on the tray menu")

    def _restore(self, why: str) -> None:
        """Bring the window back, writing down what asked for it.

        Each door has its own slot rather than one shared one, because
        knowing WHICH of them opened is the whole question when the window
        appears and nobody asked for it.
        """
        self._note(f"restoring because {why}")
        self.showNormal()
        self.raise_()
        self.activateWindow()
