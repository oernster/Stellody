"""A window choosing among stand-in devices, for the `OUTPUTS.md` UI tests.

The devices are a list the test can change under the window, which is what a
Bluetooth pair connecting does to the real one; `outputs_changed` is then
called as the signal from `OutputDevices.listed` would call it.
"""

from __future__ import annotations

import pytest

from stellody.domain.outputs import OutputChoice, OutputDevice
from stellody.ui.main_window import MainWindow
from stellody.ui.output_menu import SYSTEM_DEFAULT_LABEL

SPEAKERS = OutputDevice(identity="{speakers}", name="Speakers (Realtek)")
FOCUSRITE = OutputDevice(identity="{focusrite}", name="Speakers (Focusrite)")
BATHYS = OutputDevice(identity="{bathys}", name="Headphones (Focal Bathys)")
LISTED = (SPEAKERS, FOCUSRITE)
REASON = "held by another application"


def chose(device: OutputDevice) -> OutputChoice:
    """The choice a listener makes by picking this device."""
    return OutputChoice(identity=device.identity, name=device.name)


class Devices:
    """The system's list, as a test holds it."""

    def __init__(self, listed: tuple[OutputDevice, ...] = LISTED) -> None:
        self.listed = listed

    def __call__(self) -> tuple[OutputDevice, ...]:
        return self.listed


@pytest.fixture
def devices() -> Devices:
    return Devices()


@pytest.fixture
def choosing(
    window: MainWindow,
    devices: Devices,
) -> MainWindow:
    """The window, told which devices there are, as the composition root does."""
    window.start_choosing_outputs(devices)
    return window


def lines(menu) -> list[str]:
    """What a menu's lines say, in order."""
    return [action.text() for action in menu.actions()]


def marked(menu) -> list[str]:
    """Which of a menu's lines carry the mark."""
    return [action.text() for action in menu.actions() if action.isChecked()]


def expected_lines(devices=LISTED) -> list[str]:
    return [SYSTEM_DEFAULT_LABEL, *(device.name for device in devices)]
