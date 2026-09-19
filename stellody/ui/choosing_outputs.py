"""The window's half of choosing the output device. `OUTPUTS.md`.

The transport holds the choice and what follows from it
(`application/output_choosing.py`); this shows it in both lists, remembers it
and says on the status line what a listener would otherwise have to guess: a
device that would not open, one missing at launch, one that disconnected.

The list of devices is handed in by the composition root rather than read here,
since reading it reaches the operating system and the window reaches nothing
below the application layer.
"""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Slot

from stellody.application.output_choosing import OutputChange
from stellody.domain.outputs import OutputChoice, OutputDevice
from stellody.ui.output_menu import fill_output_menu
from stellody.ui.settings_keys import (
    SETTING_OUTPUT_DEVICE,
    SETTING_OUTPUT_DEVICE_NAME,
    UNPLAYABLE_MESSAGE_MS,
)

# FR-O08: which device, with the reason it gave.
REFUSED_MESSAGE = (
    "{name} would not open, so the music is playing through the system "
    "default: {reason}"
)
# FR-O10: said once at launch while the choice waits for its device.
MISSING_MESSAGE = (
    "{name} is not connected, so the music will play through the system "
    "default until it is."
)
# FR-O11: a loss pauses the track in hand; the press that carries on is the
# listener agreeing to the default, so the message says what the press does.
PAUSED_BY_LOSS_MESSAGE = (
    "{name} disconnected, so the music is paused. Press play to carry on "
    "through the system default."
)
LOST_MESSAGE = (
    "{name} disconnected, so the music will play through the system default "
    "until it returns."
)

ListOutputs = Callable[[], tuple[OutputDevice, ...]]


class ChoosingOutputs:
    """Choosing the output device, from the window's side. Mixed into it."""

    def start_choosing_outputs(self, list_outputs: ListOutputs) -> None:
        """Take the devices, then the choice last left, before anything plays.

        FR-O09, FR-O10. Nothing is loaded yet, so the choice only says where
        the first track will open.
        """
        self._list_outputs = list_outputs
        self._transport.outputs_listed(list_outputs())
        self._transport.choose_output(
            OutputChoice(
                identity=self._settings.get_setting(SETTING_OUTPUT_DEVICE, ""),
                name=self._settings.get_setting(SETTING_OUTPUT_DEVICE_NAME, ""),
            )
        )
        self.show_outputs()
        if self._transport.output_missing:
            self._say_about_output(
                MISSING_MESSAGE.format(name=self._transport.output_choice.name)
            )

    @Slot()
    def outputs_changed(self) -> None:
        """Take the list again: a device connected, else one went. FR-O13."""
        changes: list[OutputChange] = []
        self._drive(
            lambda: changes.append(self._transport.outputs_listed(self._list_outputs()))
        )
        if changes == [OutputChange.LOST]:
            words = (
                PAUSED_BY_LOSS_MESSAGE
                if self._transport.state.is_active
                else LOST_MESSAGE
            )
            self._say_about_output(
                words.format(name=self._transport.output_choice.name)
            )
        self.show_outputs()

    def choose_output(self, choice: OutputChoice) -> None:
        """Send the music there, show it and remember it. FR-O07, FR-O09."""
        self._drive(lambda: self._transport.choose_output(choice))
        self._settings.set_setting(SETTING_OUTPUT_DEVICE, choice.identity)
        self._settings.set_setting(SETTING_OUTPUT_DEVICE_NAME, choice.name)
        self.show_outputs()
        self.say_output_refusal()

    def say_output_refusal(self) -> None:
        """Say once that a device would not open, with its reason. FR-O08.

        Asked after every choice and on the transport's poll, since a refusal
        can come at any open: the next track as well as the choice itself.
        """
        refusal = self._transport.take_refusal()
        if refusal is None:
            return
        self._say_about_output(
            REFUSED_MESSAGE.format(name=refusal.device.name, reason=refusal.reason)
        )

    def show_outputs(self) -> None:
        """Fill both lists from the transport: the strip's and the menu's."""
        entries = self._transport.output_entries
        self._bottom_tray.sound.show_outputs(entries, self.choose_output)
        fill_output_menu(self._output_menu, entries, self.choose_output)

    def _say_about_output(self, words: str) -> None:
        self.statusBar().showMessage(words, UNPLAYABLE_MESSAGE_MS)
