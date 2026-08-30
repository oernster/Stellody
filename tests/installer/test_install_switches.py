"""What an install asks the application to do with the switches it finds.

Stellody's own directory outlives an uninstall unless the user asks for it to
go, so a reinstall used to come back wearing shuffle and repeat set months
earlier. A fresh install and a reinstall therefore ask for them off; an update
and a downgrade are the same install carrying on, so they leave every choice
alone.

Split from the setup window's own tests because this is one question with four
answers rather than part of the tour of the screens.
"""

from __future__ import annotations

import pytest
from PySide6.QtWidgets import QApplication
from test_setup_window import (
    INSTALLED_AT,
    THIS_VERSION,
    _FakeProcess,
    _here,
    _window,
)

from installer import actions, launching
from installer import app as setup
from installer.route import Route


def _anew_passed(
    monkeypatch: pytest.MonkeyPatch,
    window: setup.SetupWindow,
    reinstalling: bool = False,
) -> bool:
    """What the window asked the install for, with the install itself stood in."""
    asked: list[bool] = []

    def record(plan, archive, progress=None, anew=False):
        asked.append(anew)
        return plan.target / actions.EXE_NAME

    monkeypatch.setattr(actions, "payload_zip", lambda: INSTALLED_AT / "payload.zip")
    monkeypatch.setattr(actions, "install", record)
    # Writing the files runs on into starting them. Left alone, that started
    # the real application on the machine running the suite, on every run.
    monkeypatch.setattr(launching, "launch", lambda exe: _FakeProcess())
    monkeypatch.setattr(launching, "front", lambda pid: True)
    window._write_files(reinstalling=reinstalling)
    return asked[0]


def test_a_first_install_asks_for_the_switches_to_start_off(
    application: QApplication, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Nothing was installed, so nothing the user chose is being carried on."""
    window = _window(monkeypatch, _here())
    assert window.route is Route.INSTALL
    assert _anew_passed(monkeypatch, window) is True


def test_a_reinstall_asks_for_the_switches_to_start_off(
    application: QApplication, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The directory survives an uninstall, so the switches must not survive it."""
    window = _window(monkeypatch, _here(THIS_VERSION))
    assert window.route is Route.MANAGE
    assert _anew_passed(monkeypatch, window, reinstalling=True) is True


@pytest.mark.parametrize("installed", ("0.1.0", "0.3.0"))
def test_an_update_or_a_downgrade_leaves_the_switches_alone(
    application: QApplication, monkeypatch: pytest.MonkeyPatch, installed: str
) -> None:
    """Both are the same install carrying on, so neither resets a choice."""
    window = _window(monkeypatch, _here(installed))
    assert window.route in (Route.UPDATE, Route.DOWNGRADE)
    assert _anew_passed(monkeypatch, window) is False
