"""Every way the window can appear says so, naming what asked for it.

The fault under investigation is a window arriving with nobody having asked.
Two fixes have gone in against it and neither has been shown to be the one
that mattered, so the window now writes down every appearance along with the
frames that led there.

The doors are separate slots rather than one shared one because WHICH door
opened is the entire question. A shared slot would record that the window came
back and leave the interesting half unsaid.
"""

from __future__ import annotations

import pytest
from conftest import RecordingPlayer
from PySide6.QtWidgets import QApplication
from tray_support import RememberingStore, build


@pytest.fixture
def noted() -> list[str]:
    """Everything the window wrote down."""
    return []


@pytest.fixture
def window(application: QApplication, noted: list[str]):
    """A window that keeps an account, into a list rather than a file."""
    made = build(RememberingStore(), RecordingPlayer(), leave=lambda: None)
    made._note = noted.append
    yield made
    made._quitting = True
    made.close()
    made.deleteLater()


def test_an_appearance_is_recorded_with_the_frames_that_led_to_it(
    window, noted
) -> None:
    """The stack is what names a door nobody thought to watch."""
    window.show()
    shown = [line for line in noted if line.startswith("window shown")]
    assert shown, "an appearance that goes unrecorded is the one we cannot explain"
    assert "<-" in shown[0], "and it carries the trail, not merely the fact"
    assert "test_appearances.py" in shown[0], "which names the actual caller"


def test_the_window_going_away_is_recorded_too(window, noted) -> None:
    """Else the account cannot say whether it was ever put away."""
    window.show()
    window.hide()
    assert "window hidden" in noted


@pytest.mark.parametrize(
    ("door", "expected"),
    [
        ("restore_for_channel", "another launch asked over the channel"),
        ("restore_for_tray_icon", "the tray icon was clicked"),
        ("restore_for_tray_menu", "Show was chosen on the tray menu"),
        ("restore_from_tray", "an unnamed request"),
    ],
)
def test_each_door_names_itself(window, noted, door: str, expected: str) -> None:
    getattr(window, door)()
    assert any(
        f"restoring because {expected}" in line for line in noted
    ), f"{door} has to say it was the one that opened"


def test_a_window_given_no_diary_keeps_its_own_counsel(
    application: QApplication,
) -> None:
    """Every test but these wants a window that writes nothing anywhere."""
    made = build(RememberingStore(), RecordingPlayer(), leave=lambda: None)
    try:
        made.show()
        made.restore_for_tray_icon()
    finally:
        made._quitting = True
        made.close()
        made.deleteLater()
