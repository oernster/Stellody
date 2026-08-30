"""The setup window: which screen each route opens on, then what it offers.

The screen and its actions are the part that used to drift, because one fixed
row of buttons was relabelled as setup went along. These assert the pairing:
the route decides the screen AND the actions under it, so a destructive button
cannot arrive wearing the styling of a safe one.

Qt is never mocked. A real QApplication draws offscreen; only the machine
underneath, the registry and the filesystem, is stood in for.
"""

from __future__ import annotations

import pathlib

import pytest
from PySide6.QtWidgets import QApplication, QLabel

from installer import actions, launching, registry, running, screens, wording
from installer import app as setup
from installer.existing import Existing
from installer.footer import DANGER, PRIMARY
from installer.route import Route

INSTALLED_AT = pathlib.Path("C:/Programs/Stellody")
THIS_VERSION = "0.2.0"


@pytest.fixture(scope="session")
def application() -> QApplication:
    """One real QApplication for the whole session. Qt is never mocked."""
    existing = QApplication.instance()
    return existing or QApplication([])


def _here(version: str = "", **flags: bool) -> Existing:
    """A fabricated reading of the machine, so no test touches the real one."""
    return Existing(
        version=version,
        location=INSTALLED_AT,
        desktop=flags.get("desktop", False),
        start_menu=flags.get("start_menu", False),
        sign_in=flags.get("sign_in", False),
    )


def _window(
    monkeypatch: pytest.MonkeyPatch,
    here: Existing,
    uninstalling: bool = False,
) -> setup.SetupWindow:
    """A setup window over a fabricated machine."""
    monkeypatch.setattr(setup.existing, "look", lambda: here)
    monkeypatch.setattr(setup, "read_version", lambda: THIS_VERSION)
    monkeypatch.setattr(running, "is_running", lambda: False)
    return setup.SetupWindow(uninstalling=uninstalling)


def _labels(window: setup.SetupWindow) -> list[str]:
    """What the footer currently offers, left to right."""
    return [button.text() for button in window._footer.buttons()]


def _texts(window: setup.SetupWindow) -> list[str]:
    """Every piece of text drawn in the window."""
    return [label.text() for label in window.findChildren(QLabel)]


def test_nothing_installed_offers_only_cancel_and_install(
    application: QApplication, monkeypatch: pytest.MonkeyPatch
) -> None:
    window = _window(monkeypatch, _here())
    assert window.route is Route.INSTALL
    assert _labels(window) == ["Cancel", "Install"]


def test_a_first_install_offers_both_shortcuts_and_the_launch(
    application: QApplication, monkeypatch: pytest.MonkeyPatch
) -> None:
    window = _window(monkeypatch, _here())
    assert window._desktop.isChecked()
    assert window._start_menu.isChecked()
    assert window._launch.isChecked()


def test_the_boxes_say_what_is_already_there(
    application: QApplication, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A shortcut the user deleted was offered back as though they asked."""
    window = _window(monkeypatch, _here(THIS_VERSION, start_menu=True))
    assert window._start_menu.isChecked()
    assert not window._desktop.isChecked()


def test_starting_at_sign_in_asks_one_question_rather_than_two(
    application: QApplication, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Where it starts is settled: quietly, in the notification area."""
    window = _window(monkeypatch, _here())
    assert "notification area" in wording.SIGN_IN_HINT
    assert not hasattr(window, "_minimised")


def test_an_update_offers_a_way_out_that_is_not_the_go_ahead(
    application: QApplication, monkeypatch: pytest.MonkeyPatch
) -> None:
    window = _window(monkeypatch, _here("0.1.0"))
    assert window.route is Route.UPDATE
    assert _labels(window) == ["Uninstall", "Not now", "Update"]


def test_a_change_shows_both_versions_rather_than_naming_one(
    application: QApplication, monkeypatch: pytest.MonkeyPatch
) -> None:
    window = _window(monkeypatch, _here("0.1.0"))
    drawn = _texts(window)
    assert "v0.1.0" in drawn
    assert f"v{THIS_VERSION}" in drawn


def test_an_older_setup_over_a_newer_install_asks_about_going_back(
    application: QApplication, monkeypatch: pytest.MonkeyPatch
) -> None:
    window = _window(monkeypatch, _here("0.3.0"))
    assert window.route is Route.DOWNGRADE
    assert _labels(window) == ["Uninstall", "Not now", "Go back"]


def test_a_matching_version_offers_repair_and_reinstall(
    application: QApplication, monkeypatch: pytest.MonkeyPatch
) -> None:
    window = _window(monkeypatch, _here(THIS_VERSION))
    assert window.route is Route.MANAGE
    assert _labels(window) == ["Uninstall", "Close", "Reinstall", "Repair"]


def test_the_destructive_action_is_marked_as_one(
    application: QApplication, monkeypatch: pytest.MonkeyPatch
) -> None:
    """It used to wear the styling of the safe go-ahead."""
    window = _window(monkeypatch, _here(THIS_VERSION))
    kinds = [button.objectName() for button in window._footer.buttons()]
    assert kinds[0] == DANGER
    assert kinds[-1] == PRIMARY


def test_the_uninstall_screen_asks_before_it_takes_the_library(
    application: QApplication, monkeypatch: pytest.MonkeyPatch
) -> None:
    window = _window(monkeypatch, _here(THIS_VERSION), uninstalling=True)
    assert window._body.currentIndex() == screens.SCREEN_UNINSTALL
    assert _labels(window) == ["Cancel", "Uninstall"]
    assert not window._forget.isChecked()
    assert window._footer.buttons()[-1].objectName() == DANGER


def test_asking_to_remove_can_be_taken_back(
    application: QApplication, monkeypatch: pytest.MonkeyPatch
) -> None:
    window = _window(monkeypatch, _here(THIS_VERSION))
    window._footer.buttons()[0].click()
    assert window._body.currentIndex() == screens.SCREEN_UNINSTALL
    window._footer.buttons()[0].click()
    assert window._body.currentIndex() == screens.SCREEN_ROUTE
    assert _labels(window) == ["Uninstall", "Close", "Reinstall", "Repair"]


def test_nothing_wears_a_ring_until_one_is_asked_for(
    application: QApplication, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The house start is neutral, whatever the reference installer focuses."""
    window = _window(monkeypatch, _here())
    window.show()
    QApplication.processEvents()
    assert window.focusWidget() is window._start
    assert not any(button.hasFocus() for button in window._footer.buttons())
    window.close()


def test_work_in_progress_offers_nothing_at_all(
    application: QApplication, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A Close during work it cannot stop is an offer setup cannot honour."""
    window = _window(monkeypatch, _here())
    window._working("Installing")
    assert window._body.currentIndex() == screens.SCREEN_PROGRESS
    assert _labels(window) == []


def test_a_verdict_leaves_only_the_way_out(
    application: QApplication, monkeypatch: pytest.MonkeyPatch
) -> None:
    window = _window(monkeypatch, _here())
    window._verdict("x", "Done", "All of it")
    assert window._body.currentIndex() == screens.SCREEN_VERDICT
    assert _labels(window) == ["Close"]


def test_an_open_application_is_asked_about_before_a_file_is_touched(
    application: QApplication, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Extracting over a locked executable raises partway through."""
    window = _window(monkeypatch, _here(THIS_VERSION))
    monkeypatch.setattr(running, "is_running", lambda: True)
    window._go()
    assert window._body.currentIndex() == screens.SCREEN_RUNNING
    assert _labels(window) == ["Cancel", "Close it and continue"]


def test_declining_to_close_it_returns_to_the_screen_that_was_due(
    application: QApplication, monkeypatch: pytest.MonkeyPatch
) -> None:
    window = _window(monkeypatch, _here(THIS_VERSION), uninstalling=True)
    monkeypatch.setattr(running, "is_running", lambda: True)
    window._footer.buttons()[-1].click()
    assert window._body.currentIndex() == screens.SCREEN_RUNNING
    window._footer.buttons()[0].click()
    assert window._body.currentIndex() == screens.SCREEN_UNINSTALL


def test_a_managed_box_acts_the_moment_it_is_ticked(
    application: QApplication, monkeypatch: pytest.MonkeyPatch
) -> None:
    """On a matching version nothing else would ever apply it."""
    window = _window(monkeypatch, _here(THIS_VERSION))
    applied: list[tuple[bool, bool]] = []
    monkeypatch.setattr(
        actions,
        "set_shortcuts",
        lambda executable, desktop, start_menu: applied.append((desktop, start_menu)),
    )
    window._desktop.setChecked(True)
    assert applied == [(True, False)]


def test_a_managed_sign_in_box_writes_one_entry_either_way(
    application: QApplication, monkeypatch: pytest.MonkeyPatch
) -> None:
    window = _window(monkeypatch, _here(THIS_VERSION))
    written: list[bool] = []
    monkeypatch.setattr(
        registry,
        "write_sign_in_entry",
        lambda executable, wanted: written.append(wanted),
    )
    window._sign_in.setChecked(True)
    assert written == [True]


def test_a_box_on_a_route_that_installs_waits_for_the_go_ahead(
    application: QApplication, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An install applies its choices once, when it writes the files."""
    window = _window(monkeypatch, _here())
    applied: list[object] = []
    monkeypatch.setattr(actions, "set_shortcuts", lambda *_: applied.append(True))
    window._desktop.setChecked(False)
    assert applied == []


class _FakeProcess:
    """A launched application, as far as setup needs to know."""

    pid = 4321


def test_the_launch_box_starts_it_and_then_gets_out_of_the_way(
    application: QApplication, monkeypatch: pytest.MonkeyPatch
) -> None:
    window = _window(monkeypatch, _here())
    started: list[pathlib.Path] = []
    monkeypatch.setattr(
        launching,
        "launch",
        lambda exe, quiet=False: started.append(exe) or _FakeProcess(),
    )
    monkeypatch.setattr(launching, "front", lambda pid: True)
    executable = INSTALLED_AT / actions.EXE_NAME
    window._finish(executable, "Installed", "It is there.")
    assert started == [executable]
    assert window._front_timer.isActive()
    window._front_then_close()
    assert not window._front_timer.isActive()


def test_setup_stays_until_the_new_window_is_up(
    application: QApplication, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A window arriving after setup has gone only flashes on the taskbar."""
    window = _window(monkeypatch, _here())
    monkeypatch.setattr(launching, "launch", lambda exe, quiet=False: _FakeProcess())
    monkeypatch.setattr(launching, "front", lambda pid: False)
    window._finish(INSTALLED_AT / actions.EXE_NAME, "Installed", "It is there.")
    window._front_then_close()
    assert window._front_timer.isActive()
    window._front_deadline = 0.0
    window._front_then_close()
    assert not window._front_timer.isActive()


def test_an_unticked_launch_box_leaves_the_verdict_on_screen(
    application: QApplication, monkeypatch: pytest.MonkeyPatch
) -> None:
    window = _window(monkeypatch, _here())
    monkeypatch.setattr(
        launching, "launch", lambda exe, quiet=False: pytest.fail("not asked for")
    )
    window._launch.setChecked(False)
    window._finish(INSTALLED_AT / actions.EXE_NAME, "Installed", "It is there.")
    assert window._body.currentIndex() == screens.SCREEN_VERDICT


def test_an_application_that_will_not_start_is_reported_rather_than_hidden(
    application: QApplication, monkeypatch: pytest.MonkeyPatch
) -> None:
    window = _window(monkeypatch, _here())
    monkeypatch.setattr(launching, "launch", lambda exe, quiet=False: None)
    window._finish(INSTALLED_AT / actions.EXE_NAME, "Installed", "It is there.")
    assert "could not start it" in window._verdict_lead.text()


def test_removing_says_which_way_the_library_went(
    application: QApplication, monkeypatch: pytest.MonkeyPatch
) -> None:
    window = _window(monkeypatch, _here(THIS_VERSION), uninstalling=True)
    monkeypatch.setattr(actions, "uninstall", lambda *args, **kwargs: None)
    window._remove()
    assert "left in place" in window._verdict_lead.text()
    window._forget.setChecked(True)
    window._remove()
    assert "are gone" in window._verdict_lead.text()
