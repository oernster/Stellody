"""One Stellody at a time, with a way to call the running one forward.

Measured on a machine where the window had been closed to the notification
area: the window existed but was hidden, so it had no button on the taskbar;
clicking the pinned shortcut started a second copy rather than showing the one
already there.
"""

from __future__ import annotations

import pathlib

import pytest

from stellody.infrastructure import instance

KEY = "Stellody.tests.claim"


def test_the_first_copy_takes_the_claim_and_a_second_is_refused() -> None:
    first = instance.Claim(KEY)
    second = instance.Claim(KEY)
    try:
        assert first.take() is True
        assert second.take() is False, "a second copy is not the one that runs"
    finally:
        first.release()
        second.release()


def test_releasing_is_safe_whether_or_not_the_claim_was_taken() -> None:
    """It runs on the way out, where a fault would be the last thing said."""
    instance.Claim(KEY + ".never").release()


def test_a_note_asks_the_running_copy_to_come_forward(
    tmp_path: pathlib.Path,
) -> None:
    assert instance.asked(tmp_path) is False, "nobody has asked"
    assert instance.ask(tmp_path) is True
    assert instance.attention_path(tmp_path).is_file()
    assert instance.asked(tmp_path) is True


def test_the_note_is_read_once_and_then_gone(tmp_path: pathlib.Path) -> None:
    """A note left behind would raise the window on every tick."""
    instance.ask(tmp_path)
    assert instance.asked(tmp_path) is True
    assert instance.asked(tmp_path) is False
    assert not instance.attention_path(tmp_path).exists()


def test_nothing_is_created_where_there_is_no_directory(
    tmp_path: pathlib.Path,
) -> None:
    """No directory means nothing is running, so there is nobody to ask."""
    absent = tmp_path / "never-used"
    assert instance.ask(absent) is False
    assert not absent.exists()


def test_a_note_that_cannot_be_left_is_not_a_fault(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def refuse(*_: object, **__: object) -> None:
        raise OSError("access is denied")

    monkeypatch.setattr(pathlib.Path, "write_text", refuse)
    assert instance.ask(tmp_path) is False


def test_a_note_that_cannot_be_removed_is_read_as_no_note(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Better a window not raised than one raised over and over."""
    instance.ask(tmp_path)

    def refuse(*_: object, **__: object) -> None:
        raise OSError("in use")

    monkeypatch.setattr(pathlib.Path, "unlink", refuse)
    assert instance.asked(tmp_path) is False
