"""The note the setup program leaves; the application takes it.

It is a file rather than a write into the library database because setup runs
at the one moment that database is least safe to touch: it has just ended the
application by force. Writing there hung an install once and left the
application unable to start after another.
"""

from __future__ import annotations

import pathlib

import pytest

from stellody.infrastructure import switch_reset


def test_a_note_left_is_a_note_taken(tmp_path: pathlib.Path) -> None:
    assert switch_reset.leave(tmp_path) is True
    assert switch_reset.marker_path(tmp_path).is_file()
    assert switch_reset.take(tmp_path) is True


def test_a_note_is_read_once_and_then_gone(tmp_path: pathlib.Path) -> None:
    """A note left behind would turn every launch into a reset."""
    switch_reset.leave(tmp_path)
    assert switch_reset.take(tmp_path) is True
    assert switch_reset.take(tmp_path) is False
    assert not switch_reset.marker_path(tmp_path).exists()


def test_nothing_is_created_where_there_is_no_directory(
    tmp_path: pathlib.Path,
) -> None:
    """A machine with nothing remembered has nothing to clear."""
    absent = tmp_path / "never-used"
    assert switch_reset.leave(absent) is False
    assert not absent.exists()


def test_a_note_that_cannot_be_left_is_not_a_fault(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An install must not stop over a pair of switches."""

    def refuse(*_: object, **__: object) -> None:
        raise OSError("access is denied")

    monkeypatch.setattr(pathlib.Path, "write_text", refuse)
    assert switch_reset.leave(tmp_path) is False


def test_a_note_that_cannot_be_removed_is_read_as_no_note(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Better a switch left as it was than a reset on every launch."""
    switch_reset.leave(tmp_path)

    def refuse(*_: object, **__: object) -> None:
        raise OSError("in use")

    monkeypatch.setattr(pathlib.Path, "unlink", refuse)
    assert switch_reset.take(tmp_path) is False
