"""The account of what happened, which has to survive the thing it watches.

The fault it exists for spans processes and outlives the moment it happened,
so the file is appended rather than rewritten and carries the process id. A
diary that overwrote itself would answer every question with the last line.
"""

from __future__ import annotations

import pathlib

import pytest

from stellody.infrastructure import diary


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


def test_a_diary_that_cannot_be_written_says_nothing_and_raises_nothing(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """It watches the application; it may never be what breaks it."""
    monkeypatch.setattr(diary, "location", lambda: tmp_path / "no" / "such" / "dir.log")
    diary.note("into the void")


def test_clearing_is_safe_when_there_is_nothing_to_clear(elsewhere) -> None:
    diary.clear()
    diary.note("kept")
    diary.clear()
    assert not elsewhere.exists()
