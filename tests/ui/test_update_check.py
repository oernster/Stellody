"""The help menu, plus the update check behind one of its entries.

The check is asked on a thread of its own, so the load-bearing test here is
the one that proves the ANSWER arrives on the interface thread. A signal
connected to a bare function runs in the thread that emitted it, which would
put a dialog on the worker; the probe below is what tells the two apart,
rather than the code looking as though it is the right shape.
"""

from __future__ import annotations

import threading

import pytest
from conftest import RecordingPlayer
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication, QMessageBox
from tray_support import RememberingStore, build

from stellody.application.updates import UpdateService, platform_key_for
from stellody.application.values import ReleaseAsset, ReleaseInfo, UpdateStatus
from stellody.ui.settings_keys import SETTING_SKIPPED_UPDATE
from stellody.ui.toolbar import ABOUT_ENTRY, HELP_TOOLTIP, UPDATES_ENTRY
from stellody.ui.update_check import (
    DOWNLOAD,
    LATER,
    SKIP,
    UNREACHABLE,
    UP_TO_DATE,
    UpdateCheckController,
    offer_text,
)

CURRENT = "0.5.0"
NEWER = "0.6.0"
PAGE = "https://github.com/oernster/stellody/releases/tag/v0.6.0"
FILE_URL = "https://example.test/StellodySetup.exe"


class Source:
    """A release source answering with whatever this test needs it to."""

    def __init__(self, release: ReleaseInfo | None) -> None:
        self._release = release
        self.thread_asked_on = ""

    def latest_release(self) -> ReleaseInfo | None:
        """The prepared release, noting which thread came asking for it."""
        self.thread_asked_on = threading.current_thread().name
        return self._release


def _service(release: ReleaseInfo | None) -> UpdateService:
    """A service over one prepared answer, for this machine."""
    return UpdateService(Source(release), CURRENT, platform_key_for("win32"))


def _newer() -> ReleaseInfo:
    """A published release ahead of the running one, carrying a file."""
    return ReleaseInfo(
        version=NEWER,
        page_url=PAGE,
        assets=(ReleaseAsset("StellodySetup.exe", FILE_URL),),
    )


class Settings:
    """The two settings calls the controller is given, recorded."""

    def __init__(self, stored: str = "") -> None:
        self.values = {SETTING_SKIPPED_UPDATE: stored} if stored else {}

    def get(self, key: str, default: str = "") -> str:
        """What is stored under a key, else the default."""
        return self.values.get(key, default)

    def set(self, key: str, value: str) -> None:
        """Write a value down, as the real store does."""
        self.values[key] = value


@pytest.fixture
def window(application: QApplication):
    """A real window, built without a check so nothing runs unbidden."""
    made = build(RememberingStore(), RecordingPlayer())
    yield made
    made.close()


class TestTheHelpButton:
    """The button was About and is a way in to several things now.

    The wanted words are written out here rather than read from the module
    being guarded. Comparing a tooltip against the very constant that sets it
    proves only that the constant equals itself: put the old wording back and
    a test written that way still passes, which was measured rather than
    supposed.
    """

    def test_the_button_offers_help_rather_than_naming_one_entry(self, window) -> None:
        assert window._tray.help_button.toolTip() == "Help"
        assert HELP_TOOLTIP == "Help"

    def test_the_menu_carries_about_and_the_update_check(self, window) -> None:
        labels = [action.text() for action in window._tray.help_menu.actions()]
        assert labels == ["About", "Check for updates"]
        assert [ABOUT_ENTRY, UPDATES_ENTRY] == labels

    def test_the_menu_drops_under_the_button_and_closes_again(self, window) -> None:
        """A second press takes it down, as the volume popup behaves."""
        window.show()
        QApplication.processEvents()
        window._tray._open_help()
        assert window._tray.help_menu.isVisible()
        window._tray._open_help()
        assert not window._tray.help_menu.isVisible()

    def test_the_ring_reaches_it_where_the_about_button_used_to_be(
        self, window
    ) -> None:
        assert window._tray.ring_stops()[-1] is window._tray.help_button

    def test_asking_with_no_check_wired_is_harmless(self, window) -> None:
        """Every test that is about something else builds the window this way."""
        window.check_for_updates()


class TestTheAnswerArrivesOnTheInterfaceThread:
    """The whole reason the controller is shaped the way it is."""

    def test_the_question_is_asked_off_the_interface_thread(
        self, application, window
    ) -> None:
        source = Source(None)
        service = UpdateService(source, CURRENT, platform_key_for("win32"))
        controller = UpdateCheckController(
            service, Settings().get, Settings().set, window
        )
        controller.check_quietly()
        _spin(application, lambda: source.thread_asked_on != "")
        assert source.thread_asked_on != threading.current_thread().name

    def test_the_answer_is_handled_on_the_interface_thread(
        self, application, window, monkeypatch
    ) -> None:
        """The measurement, not the reading: where the CONTROLLER's slot ran.

        Measured through the dialog the controller itself puts up, rather than
        through a probe this test connects: a probe of its own would arrive
        here whatever the controller had done, which proves nothing about the
        controller.

        What this catches is a worker that shows the answer itself rather than
        handing it back through the signal, which was verified by planting
        exactly that. It does NOT catch a bare callable in place of the bound
        method: measured on this PySide6, a functor connection takes the SENDER
        as its context; the sender is this controller, which lives here. So
        both shapes queue to this thread and the difference the house model
        warns about needs a sender that lives on the worker instead.
        """
        ran_on: list[str] = []
        monkeypatch.setattr(
            QMessageBox,
            "information",
            lambda *_a, **_k: ran_on.append(threading.current_thread().name),
        )
        controller = UpdateCheckController(
            _service(None), Settings().get, Settings().set, window
        )
        controller.check_now()
        _spin(application, lambda: bool(ran_on))
        assert ran_on[0] == threading.current_thread().name


class TestWhatIsSaidAndWhen:
    def test_a_check_the_clock_started_says_nothing_when_there_is_nothing(
        self, application, window, monkeypatch
    ) -> None:
        said: list[str] = []
        monkeypatch.setattr(
            QMessageBox, "information", lambda *a, **_k: said.append(a[-1])
        )
        controller = UpdateCheckController(
            _service(ReleaseInfo(version=CURRENT, page_url=PAGE)),
            Settings().get,
            Settings().set,
            window,
        )
        controller._show_result(_status(reached=True), manual=False)
        controller._show_result(_status(reached=False), manual=False)
        assert said == []

    def test_a_check_somebody_asked_for_reports_both_quiet_answers(
        self, window, monkeypatch
    ) -> None:
        said: list[str] = []
        monkeypatch.setattr(
            QMessageBox, "information", lambda *a, **_k: said.append(a[-1])
        )
        controller = UpdateCheckController(
            _service(None), Settings().get, Settings().set, window
        )
        controller._show_result(_status(reached=True), manual=True)
        controller._show_result(_status(reached=False), manual=True)
        assert said == [UP_TO_DATE, UNREACHABLE]

    def test_the_offer_names_both_versions(self) -> None:
        status = UpdateStatus(current=CURRENT, latest=NEWER, update_available=True)
        assert NEWER in offer_text(status)
        assert CURRENT in offer_text(status)


class TestTheThreeButtons:
    """Download opens something, Skip writes it down, Later does neither."""

    def _offered(self, window, monkeypatch, pressed: str, opened: list[str]):
        """Put the offer up with one of its buttons already chosen."""
        monkeypatch.setattr(
            "stellody.ui.update_check.open_externally",
            lambda where: opened.append(where) or True,
        )
        monkeypatch.setattr(QMessageBox, "exec", lambda _self: 0)
        monkeypatch.setattr(
            QMessageBox,
            "clickedButton",
            lambda box: _named(box, pressed),
        )
        settings = Settings()
        controller = UpdateCheckController(
            _service(_newer()), settings.get, settings.set, window
        )
        controller._offer(
            UpdateStatus(
                current=CURRENT,
                latest=NEWER,
                update_available=True,
                download_url=FILE_URL,
                page_url=PAGE,
            )
        )
        return settings

    def test_download_opens_the_file_for_this_machine(
        self, window, monkeypatch
    ) -> None:
        opened: list[str] = []
        self._offered(window, monkeypatch, DOWNLOAD, opened)
        assert opened == [FILE_URL]

    def test_skip_writes_that_version_down(self, window, monkeypatch) -> None:
        settings = self._offered(window, monkeypatch, SKIP, [])
        assert settings.values[SETTING_SKIPPED_UPDATE] == NEWER

    def test_later_neither_opens_nor_writes(self, window, monkeypatch) -> None:
        opened: list[str] = []
        left_alone = self._offered(window, monkeypatch, LATER, opened)
        assert opened == []
        assert SETTING_SKIPPED_UPDATE not in left_alone.values

    def test_a_release_with_no_file_for_this_machine_offers_its_page(
        self, window, monkeypatch
    ) -> None:
        opened: list[str] = []
        monkeypatch.setattr(
            "stellody.ui.update_check.open_externally",
            lambda where: opened.append(where) or True,
        )
        controller = UpdateCheckController(
            _service(None), Settings().get, Settings().set, window
        )
        controller._open_download(
            UpdateStatus(current=CURRENT, latest=NEWER, page_url=PAGE)
        )
        assert opened == [PAGE]

    def test_a_desktop_that_opens_nothing_says_so(self, window, monkeypatch) -> None:
        """Silence would leave somebody pressing a button that does nothing."""
        said: list[str] = []
        monkeypatch.setattr(
            "stellody.ui.update_check.open_externally", lambda _where: False
        )
        monkeypatch.setattr(
            QMessageBox, "information", lambda *a, **_k: said.append(a[-1])
        )
        controller = UpdateCheckController(
            _service(None), Settings().get, Settings().set, window
        )
        controller._open_download(
            UpdateStatus(current=CURRENT, latest=NEWER, page_url=PAGE)
        )
        assert said


class TestWhatIsSkipped:
    def test_the_clock_honours_a_skipped_version(self, window) -> None:
        settings = Settings(stored=NEWER)
        source = Source(_newer())
        controller = UpdateCheckController(
            UpdateService(source, CURRENT, platform_key_for("win32")),
            settings.get,
            settings.set,
            window,
        )
        controller._ask(manual=False)
        _join(controller)
        assert not _last_status(source, settings, skipped=NEWER).update_available

    def test_asking_outright_ignores_it(self, window) -> None:
        """Skipping silences a prompt that speaks unbidden, not the question."""
        source = Source(_newer())
        service = UpdateService(source, CURRENT, platform_key_for("win32"))
        assert service.check("").update_available
        assert not service.check(NEWER).update_available


def _status(reached: bool) -> UpdateStatus:
    """An answer that offers nothing, either read or unreachable."""
    return UpdateStatus(current=CURRENT, latest=NEWER if reached else "")


def _last_status(source, settings, skipped: str) -> UpdateStatus:
    """What the service would have answered with that skip in place."""
    return UpdateService(source, CURRENT, platform_key_for("win32")).check(skipped)


def _named(box: QMessageBox, label: str):
    """The button on this box carrying that label."""
    for button in box.buttons():
        if button.text() == label:
            return button
    return None


def _join(controller: UpdateCheckController) -> None:
    """Let every worker the controller started finish."""
    for thread in threading.enumerate():
        if thread is not threading.current_thread() and thread.daemon:
            thread.join(timeout=2)


def _spin(application: QApplication, until, limit_ms: int = 2000) -> None:
    """Turn the event loop until something happens, else give up saying so."""
    done = {"late": False}
    QTimer.singleShot(limit_ms, lambda: done.__setitem__("late", True))
    while not until() and not done["late"]:
        application.processEvents()
    assert until(), "the answer never arrived"
