"""A startup failure has to leave something behind to read.

A packaged build has no console, so an exception on the way up is invisible:
the application does not appear and nothing says why. That happened once
straight after an install, leaving the setup program's log saying it had
started something and no other trace anywhere.
"""

from __future__ import annotations

import pathlib
import tempfile

import pytest
from PySide6.QtWidgets import QApplication

from stellody import composition
from stellody.infrastructure import paths, startup_log


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


def test_the_report_is_written_where_it_was_asked_for(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    report = tmp_path / startup_log.LOG_NAME
    monkeypatch.setattr(startup_log, "location", lambda: report)
    written = startup_log.report_failure("a traceback")
    assert written == report
    assert written.read_text(encoding="utf-8") == "a traceback"


def test_it_is_kept_in_stellody_s_own_data_directory() -> None:
    """Ruled by Oliver on 2026-09-09, the same ruling that moved the diary.

    The temporary directory is private to a sandboxed application and is
    thrown away when it closes, so on the Linux flatpak the one report saying
    why Stellody never appeared was written where nobody could read it. A
    report nobody can reach is the same as no report at all.
    """
    assert startup_log.location() == paths.data_location() / startup_log.LOG_NAME


def test_it_is_not_in_the_temporary_directory(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The defect exactly: the system temp directory is not where it goes."""
    for named in ("TMPDIR", "TEMP", "TMP"):
        monkeypatch.setenv(named, str(tmp_path))
    assert startup_log.location().parent != pathlib.Path(tempfile.gettempdir())


def test_a_missing_directory_is_made_rather_than_given_up_on(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A start can fail before anything else has made that directory."""
    report = tmp_path / "not" / "there" / "yet" / startup_log.LOG_NAME
    monkeypatch.setattr(startup_log, "location", lambda: report)
    assert startup_log.report_failure("a traceback") == report
    assert report.read_text(encoding="utf-8") == "a traceback"


def test_a_report_that_cannot_be_written_is_not_a_second_fault(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """It runs while the application is already going down.

    A file is planted where the directory would have to go, since a merely
    absent directory is no longer the unwritable case: it is made.
    """
    blocked = tmp_path / "in the way"
    blocked.write_text("not a directory", encoding="utf-8")
    monkeypatch.setattr(startup_log, "location", lambda: blocked / "report")
    assert startup_log.report_failure("a traceback") is None


def test_a_home_that_cannot_be_found_is_not_a_second_fault_either(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Asking WHERE can fail too; that failure arrives as a RuntimeError.

    A guard that caught only OSError would let the reporter replace the fault
    it was reporting, on exactly the broken machine where the report matters.
    """

    def no_home() -> pathlib.Path:
        raise RuntimeError("no home directory")

    monkeypatch.setattr(startup_log, "location", no_home)
    assert startup_log.report_failure("a traceback") is None
    startup_log.clear()


def test_an_earlier_report_is_dropped_before_a_run(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """What is there has to be about the run in hand, not about last week."""
    monkeypatch.setattr(
        startup_log, "location", lambda: tmp_path / startup_log.LOG_NAME
    )
    startup_log.report_failure("an old one")
    startup_log.clear()
    assert not startup_log.location().exists()
    startup_log.clear()


def test_a_failed_start_writes_the_reason_down_and_still_raises(
    application: QApplication, tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The instrument itself, proved by a startup that cannot succeed."""
    monkeypatch.setattr(
        startup_log, "location", lambda: tmp_path / startup_log.LOG_NAME
    )

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
