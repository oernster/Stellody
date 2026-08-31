"""Asking whether a newer Stellody exists, then saying so without nagging.

**The question is asked off this thread and answered on it.** Reading a
document over the network takes as long as it takes; a player whose window
stops painting while it waits is a worse player than one that never checked.
So a plain thread asks; the answer comes back through a signal connected to
a bound method of this object, which lives on the interface thread. That shape
is deliberate: a signal connected to a bare function runs in the thread that
EMITTED it, which would put widget calls on the worker.

**Silence is the answer to a question nobody asked.** A check the clock started
says nothing at all unless there is something to offer: no "you are up to
date", no "GitHub could not be reached". A listener who chose Check for updates
is owed all three answers, because they asked and are waiting for one.

**Skip means this version, not this feature.** The tag is written down and that
tag never prompts again, while the next release prompts normally. A listener who
asks the question themselves is told about the skipped version anyway, since
skipping silences the prompt rather than the answer.
"""

from __future__ import annotations

import threading
from collections.abc import Callable

from PySide6.QtCore import QObject, QTimer, Signal, Slot
from PySide6.QtWidgets import QMessageBox, QWidget

from stellody.application.updates import UpdateService
from stellody.application.values import UpdateStatus
from stellody.shared.version import APP_NAME
from stellody.ui.links import open_externally
from stellody.ui.settings_keys import SETTING_SKIPPED_UPDATE

# Long enough to be well clear of a window opening and a library loading. The
# check is not urgent; nothing about it should compete with starting up.
LAUNCH_DELAY_MS = 3000
HOURS_A_DAY = 24
MINUTES_AN_HOUR = 60
SECONDS_A_MINUTE = 60
MS_A_SECOND = 1000
DAILY_MS = HOURS_A_DAY * MINUTES_AN_HOUR * SECONDS_A_MINUTE * MS_A_SECOND

UP_TO_DATE = f"You are running the latest version of {APP_NAME}."
UNREACHABLE = "The update check could not reach GitHub. Please try again later."
DOWNLOAD = "Download"
SKIP = "Skip This Version"
LATER = "Later"
NO_BROWSER = "Could not open a browser for the download"


def offer_text(status: UpdateStatus) -> str:
    """What the prompt says when there is a newer version to offer."""
    return (
        f"{APP_NAME} {status.latest} is available. "
        f"You are running {status.current}."
    )


class UpdateCheckController(QObject):
    """Runs the check, remembers what was skipped and speaks when it should."""

    _result_ready = Signal(object, bool)

    def __init__(
        self,
        service: UpdateService,
        get_setting: Callable[[str, str], str],
        set_setting: Callable[[str, str], None],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent if isinstance(parent, QObject) else None)
        self._service = service
        self._get_setting = get_setting
        self._set_setting = set_setting
        self._result_ready.connect(self._show_result)
        QTimer.singleShot(LAUNCH_DELAY_MS, self.check_quietly)
        self._daily = QTimer(self)
        self._daily.setInterval(DAILY_MS)
        self._daily.timeout.connect(self.check_quietly)
        self._daily.start()

    @Slot()
    def check_quietly(self) -> None:
        """The check the clock asks for: it speaks only to offer something."""
        self._ask(manual=False)

    @Slot()
    def check_now(self) -> None:
        """The check a listener asks for: every outcome is reported."""
        self._ask(manual=True)

    def _ask(self, manual: bool) -> None:
        """Put the question on a thread of its own, however it was asked.

        A manual check ignores what was skipped, since asking the question is
        asking to be told the answer whatever was said about it before.
        """
        skipped = "" if manual else self._get_setting(SETTING_SKIPPED_UPDATE, "")
        worker = threading.Thread(target=self._run, args=(skipped, manual), daemon=True)
        worker.start()

    def _run(self, skipped: str, manual: bool) -> None:
        """Ask, on the worker thread, then hand the answer back across."""
        self._result_ready.emit(self._service.check(skipped), manual)

    @Slot(object, bool)
    def _show_result(self, status: UpdateStatus, manual: bool) -> None:
        """Say what was found, on the interface thread, if anything is owed."""
        if status.update_available:
            self._offer(status)
            return
        if not manual:
            return
        self._say(UP_TO_DATE if status.reached else UNREACHABLE)

    def _say(self, message: str) -> None:
        """One plain statement, for the two answers that offer nothing."""
        QMessageBox.information(self.parent_widget(), APP_NAME, message)

    def _offer(self, status: UpdateStatus) -> None:
        """Offer the newer version, with a way to refuse it for good."""
        box = QMessageBox(self.parent_widget())
        box.setWindowTitle(APP_NAME)
        box.setText(offer_text(status))
        download = box.addButton(DOWNLOAD, QMessageBox.ButtonRole.AcceptRole)
        skip = box.addButton(SKIP, QMessageBox.ButtonRole.DestructiveRole)
        box.addButton(LATER, QMessageBox.ButtonRole.RejectRole)
        box.exec()
        pressed = box.clickedButton()
        if pressed is download:
            self._open_download(status)
        elif pressed is skip:
            self._set_setting(SETTING_SKIPPED_UPDATE, status.latest)

    def _open_download(self, status: UpdateStatus) -> None:
        """Hand the desktop the file for this machine, else the release page.

        The page is the fallback rather than nothing at all: a release with no
        file for this platform still lists every file it does carry, which is
        more use than a button that appears to do nothing.
        """
        where = status.download_url or status.page_url
        if where and open_externally(where):
            return
        self._say(NO_BROWSER)

    def parent_widget(self) -> QWidget | None:
        """The window to sit over; None when this was built without one."""
        found = self.parent()
        return found if isinstance(found, QWidget) else None
