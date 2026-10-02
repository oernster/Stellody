"""An update check whose window has gone before its answer comes back.

Found on 2026-10-02 in a full run slowed by collecting after every test: the
worker emitted its answer through a controller Qt had already deleted; the
thread died with "Signal source has been deleted". The same happens to a
listener who quits while a check is out, since the window takes the controller
with it. Nobody is left to tell, so the answer is dropped; what must not happen
is an exception escaping a thread this application started.
"""

from __future__ import annotations

import threading

import shiboken6
from update_support import CURRENT, Settings

from stellody.application.updates import UpdateService, platform_key_for
from stellody.application.values import ReleaseInfo
from stellody.ui.update_check import UpdateCheckController

# Far longer than a check against a stand-in takes, so only a hang reaches it.
WAIT_SECONDS = 5


class HeldSource:
    """A release source that answers only once the test lets it."""

    def __init__(self) -> None:
        self.asked = threading.Event()
        self.answer = threading.Event()
        self.worker: threading.Thread | None = None

    def latest_release(self) -> ReleaseInfo | None:
        """Say it has been asked, then wait to be allowed to answer."""
        self.worker = threading.current_thread()
        self.asked.set()
        self.answer.wait(WAIT_SECONDS)
        return None


def test_an_answer_with_nowhere_to_go_is_dropped_not_raised(
    application, monkeypatch
) -> None:
    escaped: list[BaseException | None] = []
    monkeypatch.setattr(
        threading, "excepthook", lambda raised: escaped.append(raised.exc_value)
    )
    source = HeldSource()
    settings = Settings()
    controller = UpdateCheckController(
        UpdateService(source, CURRENT, platform_key_for("win32")),
        settings.get,
        settings.set,
    )
    controller.check_now()
    assert source.asked.wait(WAIT_SECONDS), "the check never started"
    shiboken6.delete(controller)
    source.answer.set()
    source.worker.join(WAIT_SECONDS)
    assert not source.worker.is_alive(), "the check never finished"
    assert escaped == []
