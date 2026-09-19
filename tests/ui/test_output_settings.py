"""The choice of output device outlasts a launch. `OUTPUTS.md` FR-O09.

Stored by identity, since names repeat; the name beside it, since a device
that is missing cannot be asked its name.
"""

from __future__ import annotations

from output_support import FOCUSRITE, Devices, choosing, chose, devices
from playback_support import player, window
from recording_player import RecordingPlayer

from stellody.domain.outputs import SYSTEM_DEFAULT
from stellody.ui.settings_keys import SETTING_OUTPUT_DEVICE, SETTING_OUTPUT_DEVICE_NAME

__all__ = ["choosing", "devices", "player", "window"]


def test_the_choice_is_stored_by_identity_with_its_name(choosing) -> None:
    choosing.choose_output(chose(FOCUSRITE))
    assert choosing._settings.get_setting(SETTING_OUTPUT_DEVICE, "") == (
        FOCUSRITE.identity
    )
    assert choosing._settings.get_setting(SETTING_OUTPUT_DEVICE_NAME, "") == (
        FOCUSRITE.name
    )


def test_the_choice_outlasts_a_launch(
    window, devices: Devices, player: RecordingPlayer
) -> None:
    """What the store holds is where the first track opens."""
    window._settings.set_setting(SETTING_OUTPUT_DEVICE, FOCUSRITE.identity)
    window._settings.set_setting(SETTING_OUTPUT_DEVICE_NAME, FOCUSRITE.name)
    window.start_choosing_outputs(devices)
    assert window._transport.output_choice == chose(FOCUSRITE)
    assert player.device == FOCUSRITE


def test_nothing_stored_is_the_system_default(choosing, player) -> None:
    assert choosing._transport.output_choice == SYSTEM_DEFAULT
    assert player.device is None


def test_going_back_to_the_default_stores_nothing(choosing) -> None:
    choosing.choose_output(chose(FOCUSRITE))
    choosing.choose_output(SYSTEM_DEFAULT)
    assert choosing._settings.get_setting(SETTING_OUTPUT_DEVICE, "x") == ""
