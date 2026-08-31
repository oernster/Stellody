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
from PySide6.QtWidgets import QApplication, QSystemTrayIcon

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
        """Honour the stored close behaviour, asking when none is stored.

        The size is written down first, on every path out. The cross can leave
        Stellody running in the notification area and the tray's Quit then
        closes a window that is already hidden, so a later reading would be of
        a window that is no longer showing what it was left at.
        """
        self.remember_geometry()
        if self._quitting or not self._notification.isVisible():
            self._note(
                f"closing for good: quitting={self._quitting} "
                f"tray={self._notification.isVisible()}"
            )
            self._leave_for_good(event)
            return
        action = self._settings.get_setting(SETTING_CLOSE, CloseAction.ASK.value)
        self._note(f"the stored close action reads {action!r}")
        if action == CloseAction.ASK.value:
            action = self._ask_close_action()
        self._note(f"the close button means: {action}")
        if action == CloseAction.ASK.value:
            # The prompt was dismissed rather than answered, so the press that
            # opened it is taken back whole: the window neither leaves nor
            # hides. Anything else would act on a decision nobody made.
            event.ignore()
            return
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
        self._note("letting go of any measurement in flight")
        self.stop_shapes()
        self._note("letting go of any cover being read")
        self.stop_covering()
        self._note("letting go of any cover being looked up")
        self.stop_choosing()
        self._note("scan runner done; accepting the close")
        event.accept()
        self._note("calling the departure")
        depart = self._leave or QApplication.quit
        depart()
        self._note("the departure returned; the event loop should now end")

    def _ask_close_action(self) -> str:
        """Ask what closing should mean, defaulting to staying in the tray.

        The asking is written down on both sides of the answer. Whether this
        dialog ever reached the screen was the question in a report that it
        had gone missing; a note only after the fact cannot tell a dialog
        somebody answered from one that was never seen.
        """
        self._note("asking what the close button should mean")
        prompt = ClosePrompt(self)
        prompt.exec()
        self._note(
            f"the prompt was answered {prompt.choice.value}, "
            f"answered: {prompt.answered}, remember: {prompt.remember}"
        )
        # Only an answer is written down. The remember box is a question about
        # the choice, so a dialog waved away has nothing for it to remember;
        # keeping the tick would have made a non-answer the standing behaviour.
        if prompt.answered and prompt.remember:
            self._settings.set_setting(SETTING_CLOSE, prompt.choice.value)
        return prompt.choice.value

    @property
    def asks_on_close(self) -> bool:
        """Whether the close button still asks rather than acting on a memory."""
        stored = self._settings.get_setting(SETTING_CLOSE, CloseAction.ASK.value)
        return stored == CloseAction.ASK.value

    @Slot()
    def forget_close_choice(self) -> None:
        """Take back the answer the remember box kept.

        A choice offered with a box marked remember has to be undoable, else
        one tick is permanent and the only way back is to go and find where
        the application keeps its settings. It reaches the tray menu as well
        as this one, because the window is hidden exactly when somebody most
        wants it back.
        """
        self._settings.set_setting(SETTING_CLOSE, CloseAction.ASK.value)
        self._note("the remembered close choice was taken back")

    @property
    def tray_active(self) -> bool:
        """True when there is a notification area for the window to live in.

        Starting hidden is only honest while this holds; without a tray there
        would be nothing on screen at all.

        Measured across two launches of the same binary: the icon reported
        itself visible on one and not on the other, because an icon shown a
        moment ago has not necessarily been taken up by the shell yet. A
        launch asked to be quiet would then open a window instead, which is
        the opposite of what was asked for. Whether the platform HAS a
        notification area does not wobble like that, so it is asked as well;
        an icon already visible is answer enough on its own.
        """
        return self._notification.isVisible() or QSystemTrayIcon.isSystemTrayAvailable()

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
