"""Setup tells every route that writes the files which screen it is on.

A fresh install, a repair and a reinstall open the window maximised on that
screen. An update is told too: it is the install that decides an update leaves
no note, which `test_actions.py` holds.
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
from stellody.infrastructure.window_reset import WindowNote

OLDER_VERSION = "0.1.0"


def _quietly(monkeypatch: pytest.MonkeyPatch) -> None:
    """Nothing is extracted and nothing is started on the machine running this."""
    monkeypatch.setattr(actions, "payload_zip", lambda: INSTALLED_AT / "payload.zip")
    monkeypatch.setattr(launching, "launch", lambda exe: _FakeProcess())
    monkeypatch.setattr(launching, "front", lambda pid: True)


def _its_screen(window: setup.SetupWindow) -> WindowNote:
    """The screen the setup window is on, as the note names one."""
    screen = window.screen()
    corner = screen.geometry().topLeft()
    return WindowNote(name=screen.name(), origin=(corner.x(), corner.y()))


@pytest.mark.parametrize(
    ("installed", "reinstalling"),
    (("", False), (THIS_VERSION, True), (OLDER_VERSION, False)),
)
def test_every_install_is_told_the_screen(
    application: QApplication,
    monkeypatch: pytest.MonkeyPatch,
    installed: str,
    reinstalling: bool,
) -> None:
    window = _window(monkeypatch, _here(installed))
    told: list[WindowNote | None] = []

    def record(plan, archive, progress=None, anew=False, where=None):
        told.append(where)
        return plan.target / actions.EXE_NAME

    _quietly(monkeypatch)
    monkeypatch.setattr(actions, "install", record)
    window._write_files(reinstalling=reinstalling)
    assert told == [_its_screen(window)]


def test_a_repair_is_told_the_screen(
    application: QApplication, monkeypatch: pytest.MonkeyPatch
) -> None:
    window = _window(monkeypatch, _here(THIS_VERSION))
    assert window.route is Route.MANAGE
    told: list[WindowNote | None] = []

    def record(target, archive, progress=None, where=None):
        told.append(where)
        return target / actions.EXE_NAME

    _quietly(monkeypatch)
    monkeypatch.setattr(actions, "repair", record)
    window._repair()
    assert told == [_its_screen(window)]
