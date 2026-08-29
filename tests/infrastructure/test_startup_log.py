"""A startup failure has to leave something behind to read.

A packaged build has no console, so an exception on the way up is invisible:
the application does not appear and nothing says why. That happened once
straight after an install, leaving the setup program's log saying it had
started something and no other trace anywhere.
"""

from __future__ import annotations

import pathlib

import pytest

from stellody import composition
from stellody.infrastructure import startup_log


class Boom(RuntimeError):
    """A startup fault of the kind that used to vanish."""


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
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The instrument itself, proved by a startup that cannot succeed."""
    monkeypatch.setattr(startup_log.tempfile, "gettempdir", lambda: str(tmp_path))

    def refuse(*_: object) -> None:
        raise Boom("database is locked")

    monkeypatch.setattr(composition, "SqliteLibraryStore", refuse)
    with pytest.raises(Boom):
        composition.main([])
    written = (tmp_path / startup_log.LOG_NAME).read_text(encoding="utf-8")
    assert "Boom: database is locked" in written
    assert "_start" in written, "and where it happened"
