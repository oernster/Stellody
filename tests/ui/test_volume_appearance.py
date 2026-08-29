"""The volume slider has to be readable, which the default styling was not.

Measured before this was written: with no rules of its own the handle rendered
at 1.36:1 against the popup behind it, so the only part of the control that
read was the filled portion of the groove. These are the two properties that
kept it visible; a rule quietly dropped puts the handle back where it was.
"""

from __future__ import annotations

import re

import pytest

from stellody.ui.theme import Mode, palette_for, stylesheet

HANDLE = re.compile(r"QSlider#Volume::handle:vertical\s*\{([^{}]*)\}")
GROOVE = re.compile(r"QSlider#Volume::groove:vertical\s*\{([^{}]*)\}")
FILL = re.compile(r"QSlider#Volume::add-page:vertical\s*\{([^{}]*)\}")
POPUP = re.compile(r"QFrame#VolumePopup\s*\{([^{}]*)\}")


def block(pattern: re.Pattern[str], sheet: str) -> str:
    """The declarations of the one rule this pattern names."""
    found = pattern.search(sheet)
    assert found, f"no rule matching {pattern.pattern}"
    return found.group(1)


@pytest.mark.parametrize("mode", tuple(Mode))
def test_the_handle_carries_a_fill_and_an_outline_that_differ(mode: Mode) -> None:
    """One of the two reads against the groove; the other against the fill."""
    colour = palette_for(mode)
    declarations = block(HANDLE, stylesheet(mode))
    assert f"background-color: {colour.text}" in declarations
    assert f"solid {colour.window}" in declarations
    assert colour.text != colour.window


@pytest.mark.parametrize("mode", tuple(Mode))
def test_the_groove_and_its_filled_part_are_told_apart(mode: Mode) -> None:
    """A groove the same colour as its fill says nothing about the level."""
    colour = palette_for(mode)
    sheet = stylesheet(mode)
    assert f"background-color: {colour.window}" in block(GROOVE, sheet)
    assert f"background-color: {colour.accent}" in block(FILL, sheet)
    assert colour.window != colour.accent


@pytest.mark.parametrize("mode", tuple(Mode))
def test_the_popup_is_bounded_so_it_reads_as_a_panel(mode: Mode) -> None:
    """It floats over the window, so it needs an edge of its own."""
    colour = palette_for(mode)
    declarations = block(POPUP, stylesheet(mode))
    assert f"background-color: {colour.surface}" in declarations
    assert f"solid {colour.border}" in declarations


SWITCH_ON = re.compile(r"QPushButton#TrayButton:checked\s*\{([^{}]*)\}")


@pytest.mark.parametrize("mode", tuple(Mode))
def test_a_switch_that_is_on_is_filled_rather_than_struck_through(mode: Mode) -> None:
    """Shuffle and repeat say they are on by being lit, so the fill must read."""
    colour = palette_for(mode)
    declarations = block(SWITCH_ON, stylesheet(mode))
    assert f"background-color: {colour.accent}" in declarations
    assert colour.accent != colour.window, "against the strip it sits on"
    assert colour.accent != colour.ring, "and against its own focus border"
