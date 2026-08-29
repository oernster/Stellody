"""A startup failure has to leave something behind to read.

A packaged build has no console, so an exception on the way up is invisible:
the application does not appear and nothing says why. That happened once
straight after an install, leaving the setup program's log saying it had
started something and no other trace anywhere.
"""

from __future__ import annotations

import pathlib

import pytest
from PySide6.QtWidgets import QApplication

from stellody import composition
from stellody.infrastructure import startup_log


@pytest.fixture(scope="session")
def application() -> QApplication:
    """One real QApplication for the run. Qt is never mocked."""
    existing = QApplication.instance()
    return existing or QApplication([])


class Boom(RuntimeError):
    """A startup fault of the kind that used to vanish."""


class AlwaysTheFirst:
    """A claim nobody else holds, so startup carries on into the fault."""

    def __init__(self, *_: object) -> None:
        self.released = False

    def take(self) -> bool:
        """This copy is the one that runs."""
        return True

    def listen(self, when_asked) -> bool:
        """Never reached: startup fails before there is a window to show."""
        return True

    def release(self) -> None:
        """Nor is this, since the fault is raised on the way up."""
        self.released = True


def test_the_report_lands_beside_the_setup_programs_own_log(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(startup_log.tempfile, "gettempdir", lambda: str(tmp_path))
    written = startup_log.report_failure("a traceback")
    assert written == tmp_path / startup_log.LOG_NAME
    assert written.read_text(encoding="utf-8") == "a traceback"


def test_a_report_that_cannot_be_written_is_not_a_second_fault(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """It runs while the application is already going down."""
    monkeypatch.setattr(startup_log, "location", lambda: tmp_path / "no" / "where")
    assert startup_log.report_failure("a traceback") is None


def test_an_earlier_report_is_dropped_before_a_run(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """What is there has to be about the run in hand, not about last week."""
    monkeypatch.setattr(startup_log.tempfile, "gettempdir", lambda: str(tmp_path))
    startup_log.report_failure("an old one")
    startup_log.clear()
    assert not startup_log.location().exists()
    startup_log.clear()


def test_a_failed_start_writes_the_reason_down_and_still_raises(
    application: QApplication, tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The instrument itself, proved by a startup that cannot succeed."""
    monkeypatch.setattr(startup_log.tempfile, "gettempdir", lambda: str(tmp_path))

    def refuse(*_: object) -> None:
        raise Boom("database is locked")

    # Both of them, plus the path: a patch that misses lets main build a real
    # window against the real database and sit in Qt's event loop forever,
    # which is exactly what happened when open_store was introduced.
    monkeypatch.setattr(composition, "database_path", lambda: tmp_path / "library")
    monkeypatch.setattr(composition, "open_store", refuse)
    # And the claim. Without it this asserts nothing whenever a real Stellody
    # is running on the machine the tests are run on, since the second copy
    # would leave quietly instead of ever reaching the store.
    monkeypatch.setattr(composition.instance, "SingleInstance", AlwaysTheFirst)
    # There is one QApplication for the run and Qt allows no second one, so
    # startup is handed the one that already exists.
    monkeypatch.setattr(composition, "QApplication", lambda argv: application)
    with pytest.raises(Boom):
        composition.main([])
    written = (tmp_path / startup_log.LOG_NAME).read_text(encoding="utf-8")
    assert "Boom: database is locked" in written
    assert "_start" in written, "and where it happened"
