"""The account of what happened, which has to survive the thing it watches.

The fault it exists for spans processes and outlives the moment it happened,
so the file is appended rather than rewritten and carries the process id. A
diary that overwrote itself would answer every question with the last line.
"""

from __future__ import annotations

import pathlib
import tempfile

import pytest

from stellody.infrastructure import diary, paths

# The real answer, taken at import time. An autouse fixture in the suite's
# conftest points `diary.location` at a temporary file for every test, which
# is what stops a test run writing into the account of real runs; the two
# cases below are about where the shipped application puts it, so they need
# the function itself rather than the stand-in.
WHERE_IT_REALLY_GOES = diary.location


@pytest.fixture
def elsewhere(tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch):
    """Keep the account in a temporary directory, never the real one."""
    report = tmp_path / diary.LOG_NAME
    monkeypatch.setattr(diary, "location", lambda: report)
    return report


def test_one_note_carries_the_time_the_process_and_the_message(elsewhere) -> None:
    diary.note("something happened")
    written = elsewhere.read_text(encoding="utf-8")
    assert "something happened" in written
    assert "pid" in written, "which copy said it is half the question"
    assert written.startswith("20"), "and when it said it is the other half"


def test_notes_accumulate_rather_than_replacing_each_other(elsewhere) -> None:
    """The interesting run is usually the one before the one being read."""
    diary.note("first")
    diary.note("second")
    assert elsewhere.read_text(encoding="utf-8").count("\n") == 2


def test_the_account_starts_again_once_it_grows_too_large(elsewhere) -> None:
    """A player left running for weeks must not fill a disk with its notes."""
    elsewhere.write_text("x" * (diary.KEEP_BYTES + 1), encoding="utf-8")
    diary.note("after the cap")
    written = elsewhere.read_text(encoding="utf-8")
    assert "after the cap" in written
    assert "x" not in written, "the old account was let go"


def test_a_missing_directory_is_made_rather_than_given_up_on(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The first note can come before anything has opened the database.

    Nothing else would have made the directory by then, so a diary that only
    wrote into a directory somebody else had made would be silent about
    exactly the part of a launch it exists to describe.
    """
    report = tmp_path / "not" / "there" / "yet" / diary.LOG_NAME
    monkeypatch.setattr(diary, "location", lambda: report)
    diary.note("written on the way up")
    assert "written on the way up" in report.read_text(encoding="utf-8")


def test_a_diary_that_cannot_be_written_says_nothing_and_raises_nothing(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """It watches the application; it may never be what breaks it.

    A file is planted where the directory would have to go, so making it
    cannot succeed however hard this tries. A merely absent directory is no
    longer the unwritable case: it is made.
    """
    blocked = tmp_path / "in the way"
    blocked.write_text("not a directory", encoding="utf-8")
    monkeypatch.setattr(diary, "location", lambda: blocked / diary.LOG_NAME)
    diary.note("into the void")
    assert blocked.read_text(encoding="utf-8") == "not a directory"


def test_it_is_kept_in_stellody_s_own_data_directory() -> None:
    """Ruled by Oliver on 2026-09-09, after a diary was asked for on Linux.

    The temporary directory is private to a sandboxed application and is
    thrown away when it closes, so the flatpak wrote its diary where nobody
    could read it. This file exists to be read after the run it describes, so
    it belongs where the database is: the same directory inside a sandbox and
    out of it.
    """
    assert WHERE_IT_REALLY_GOES() == paths.data_location() / diary.LOG_NAME
    assert WHERE_IT_REALLY_GOES().parent == paths.data_location()


def test_it_is_not_in_the_temporary_directory(
    monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path
) -> None:
    """The defect exactly: the system temp directory is not where it goes."""
    monkeypatch.setenv("TMPDIR", str(tmp_path))
    monkeypatch.setenv("TEMP", str(tmp_path))
    monkeypatch.setenv("TMP", str(tmp_path))
    assert WHERE_IT_REALLY_GOES().parent != pathlib.Path(tempfile.gettempdir())


def test_clearing_is_safe_when_there_is_nothing_to_clear(elsewhere) -> None:
    diary.clear()
    diary.note("kept")
    diary.clear()
    assert not elsewhere.exists()
