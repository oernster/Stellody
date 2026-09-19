"""What the status line says about the output device. `OUTPUTS.md`.

FR-O08 a refusal, FR-O10 a device missing at launch, FR-O11 a disconnect.
Each is something a listener would otherwise have to guess.
"""

from __future__ import annotations

from output_support import (
    BATHYS,
    FOCUSRITE,
    LISTED,
    REASON,
    Devices,
    choosing,
    chose,
    devices,
)
from playback_support import album, player, window
from recording_player import RecordingPlayer

from stellody.ui.choosing_outputs import (
    LOST_MESSAGE,
    MISSING_MESSAGE,
    PAUSED_BY_LOSS_MESSAGE,
    REFUSED_MESSAGE,
)
from stellody.ui.settings_keys import SETTING_OUTPUT_DEVICE, SETTING_OUTPUT_DEVICE_NAME

__all__ = ["choosing", "devices", "player", "window"]


def _said(window) -> str:
    return window.statusBar().currentMessage()


def _playing(window) -> None:
    held = album()
    window._transport.play_album(held, held.ordered_tracks()[0])


def test_a_refusal_is_said(choosing, player: RecordingPlayer) -> None:
    """FR-O08: which device, with the reason it gave."""
    _playing(choosing)
    player.refuses = {FOCUSRITE.identity: REASON}
    choosing.choose_output(chose(FOCUSRITE))
    assert _said(choosing) == REFUSED_MESSAGE.format(name=FOCUSRITE.name, reason=REASON)


def test_a_refusal_at_the_next_track_is_said_by_the_poll(
    choosing, player: RecordingPlayer
) -> None:
    """A refusal can come at any open, not only at the choice."""
    choosing.choose_output(chose(FOCUSRITE))
    player.refuses = {FOCUSRITE.identity: REASON}
    _playing(choosing)
    choosing._poll_transport()
    assert _said(choosing) == REFUSED_MESSAGE.format(name=FOCUSRITE.name, reason=REASON)


def test_a_missing_device_is_said_once(window, devices: Devices) -> None:
    """FR-O10: the Bathys remembered while switched off."""
    window._settings.set_setting(SETTING_OUTPUT_DEVICE, BATHYS.identity)
    window._settings.set_setting(SETTING_OUTPUT_DEVICE_NAME, BATHYS.name)
    window.start_choosing_outputs(devices)
    assert _said(window) == MISSING_MESSAGE.format(name=BATHYS.name)
    assert window._transport.output_missing


def test_a_disconnect_while_playing_is_said(choosing, devices: Devices) -> None:
    """FR-O11: paused, with what the next press does."""
    devices.listed = (*LISTED, BATHYS)
    choosing.outputs_changed()
    choosing.choose_output(chose(BATHYS))
    _playing(choosing)
    devices.listed = LISTED
    choosing.outputs_changed()
    assert _said(choosing) == PAUSED_BY_LOSS_MESSAGE.format(name=BATHYS.name)


def test_a_disconnect_with_nothing_playing_is_said(choosing, devices: Devices) -> None:
    devices.listed = (*LISTED, BATHYS)
    choosing.outputs_changed()
    choosing.choose_output(chose(BATHYS))
    devices.listed = LISTED
    choosing.outputs_changed()
    assert _said(choosing) == LOST_MESSAGE.format(name=BATHYS.name)


def test_a_new_device_says_nothing(choosing, devices: Devices) -> None:
    choosing.statusBar().clearMessage()
    devices.listed = (*LISTED, BATHYS)
    choosing.outputs_changed()
    assert _said(choosing) == ""
