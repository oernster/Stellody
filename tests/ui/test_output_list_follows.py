"""The list keeps up with the devices, with no relaunch. `OUTPUTS.md` FR-O13.

The Bathys connecting while Stellody runs appears in both lists, including
one already open; leaving, it goes, unless it is the choice (FR-O14).
"""

from __future__ import annotations

from output_support import (
    BATHYS,
    LISTED,
    Devices,
    choosing,
    chose,
    devices,
    expected_lines,
    lines,
)
from playback_support import player, window

from stellody.ui.output_menu import NOT_CONNECTED_LABEL, pop_up_above

__all__ = ["choosing", "devices", "player", "window"]


def test_a_new_device_appears(choosing, devices: Devices) -> None:
    devices.listed = (*LISTED, BATHYS)
    choosing.outputs_changed()
    assert lines(choosing._bottom_tray.sound.output_menu) == expected_lines(
        devices.listed
    )
    assert lines(choosing._output_menu) == expected_lines(devices.listed)


def test_a_new_device_appears_in_a_list_already_open(
    choosing, devices: Devices
) -> None:
    sound = choosing._bottom_tray.sound
    pop_up_above(sound.output_menu, sound.output_button)
    devices.listed = (*LISTED, BATHYS)
    choosing.outputs_changed()
    assert sound.output_menu.isVisible()
    assert BATHYS.name in lines(sound.output_menu)


def test_a_removed_device_leaves(choosing, devices: Devices) -> None:
    devices.listed = (*LISTED, BATHYS)
    choosing.outputs_changed()
    devices.listed = LISTED
    choosing.outputs_changed()
    assert lines(choosing._bottom_tray.sound.output_menu) == expected_lines()


def _chose_then_lost(choosing, devices: Devices) -> None:
    devices.listed = (*LISTED, BATHYS)
    choosing.outputs_changed()
    choosing.choose_output(chose(BATHYS))
    devices.listed = LISTED
    choosing.outputs_changed()


def test_a_removed_choice_stays_listed_not_connected(
    choosing, devices: Devices
) -> None:
    """FR-O14: what will happen when it returns stays in sight."""
    _chose_then_lost(choosing, devices)
    menu = choosing._bottom_tray.sound.output_menu
    assert lines(menu)[-1] == NOT_CONNECTED_LABEL.format(name=BATHYS.name)


def test_the_tick_moves_to_where_the_music_goes(choosing, devices: Devices) -> None:
    """Amendment 5: System default is ticked while the choice is away."""
    _chose_then_lost(choosing, devices)
    for menu in (choosing._bottom_tray.sound.output_menu, choosing._output_menu):
        ticked = [action.isChecked() for action in menu.actions()]
        assert ticked == [True] + [False] * (len(ticked) - 1)


def test_the_tick_goes_back_with_the_device(choosing, devices: Devices) -> None:
    """FR-O12: the choice was kept, so its return takes the tick too."""
    _chose_then_lost(choosing, devices)
    devices.listed = (*LISTED, BATHYS)
    choosing.outputs_changed()
    menu = choosing._bottom_tray.sound.output_menu
    assert [action.text() for action in menu.actions() if action.isChecked()] == [
        BATHYS.name
    ]
