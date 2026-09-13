"""The note setup leaves so the window opens afresh; the application takes it.

A fresh install, a repair and a reinstall open maximised on the monitor setup
was on, whatever an earlier install remembered. The note names that monitor.
"""

from __future__ import annotations

import pathlib

import pytest

from stellody.infrastructure import window_reset
from stellody.infrastructure.window_reset import WindowNote

WHERE = WindowNote(name="U13NA", origin=(-223, 1440))


def test_a_note_left_is_the_note_taken(tmp_path: pathlib.Path) -> None:
    assert window_reset.leave(tmp_path, WHERE) is True
    assert window_reset.take(tmp_path) == WHERE


def test_a_note_is_read_once_and_then_gone(tmp_path: pathlib.Path) -> None:
    """A note left behind would open every launch maximised."""
    window_reset.leave(tmp_path, WHERE)
    assert window_reset.take(tmp_path) == WHERE
    assert window_reset.take(tmp_path) is None
    assert not window_reset.marker_path(tmp_path).exists()


def test_no_note_asks_for_nothing(tmp_path: pathlib.Path) -> None:
    assert window_reset.take(tmp_path) is None


def test_a_machine_with_no_directory_still_gets_its_note(
    tmp_path: pathlib.Path,
) -> None:
    """Nothing is remembered to clear on a fresh machine; a screen is still named."""
    absent = tmp_path / "never-used"
    assert window_reset.leave(absent, WHERE) is True
    assert window_reset.take(absent) == WHERE


def test_a_screen_nobody_could_name_still_asks_for_a_fresh_window(
    tmp_path: pathlib.Path,
) -> None:
    window_reset.leave(tmp_path, WindowNote())
    assert window_reset.take(tmp_path) == WindowNote()


@pytest.mark.parametrize(
    "written", ("not json", "[1, 2]", '{"screen": 3, "x": "left", "y": true}')
)
def test_a_note_that_cannot_be_read_still_asks_for_a_fresh_window(
    tmp_path: pathlib.Path, written: str
) -> None:
    """Setup asked; only what it said about where could not be read."""
    window_reset.marker_path(tmp_path).write_text(written, encoding="utf-8")
    assert window_reset.take(tmp_path) == WindowNote()


def test_a_note_that_cannot_be_left_is_not_a_fault(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An install must not stop over where a window opens."""

    def refuse(*_: object, **__: object) -> None:
        raise OSError("access is denied")

    monkeypatch.setattr(pathlib.Path, "write_text", refuse)
    assert window_reset.leave(tmp_path, WHERE) is False


def test_a_note_that_cannot_be_removed_is_read_as_no_note(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Better a window as it was left than one maximised on every launch."""
    window_reset.leave(tmp_path, WHERE)

    def refuse(*_: object, **__: object) -> None:
        raise OSError("in use")

    monkeypatch.setattr(pathlib.Path, "unlink", refuse)
    assert window_reset.take(tmp_path) is None
