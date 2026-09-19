"""Which output device the music goes to; what choosing one does.

`OUTPUTS.md` is the specification. The rules about the list itself live in
`domain/outputs.py`; this is what a transport does with them. A choice is
kept apart from the device in use. The two differ while the chosen device is
missing and after it refused to open; either way the music plays on the
system default while the choice waits.

Mixed into the transport beside `OutputFollowing`, which pauses for a move of
the system default. The two meet in one place: a move of the default is
nothing to music playing on a named device.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from stellody.application.playback_ports import OutputRefused, PlaybackPort
from stellody.domain.outputs import (
    SYSTEM_DEFAULT,
    OutputChoice,
    OutputDevice,
    OutputEntry,
    device_in_use,
    output_list,
)
from stellody.domain.playback import OutputRequest
from stellody.domain.track import TrackSource


class OutputChange(Enum):
    """What a new list of devices did to the device in use."""

    NONE = "none"
    LOST = "lost"
    RETURNED = "returned"


@dataclass(frozen=True, slots=True)
class Refusal:
    """A device that would not open, with the reason it gave. FR-O08."""

    device: OutputDevice
    reason: str


class OutputChoosing:
    """The choice of device and what follows from it. Mixed into the transport."""

    _player: PlaybackPort

    def _forget_outputs(self) -> None:
        """Start on the system default, with no device yet listed."""
        self._outputs: tuple[OutputDevice, ...] = ()
        self._choice = SYSTEM_DEFAULT
        self._in_use: OutputDevice | None = None
        # The identity of a device that refused, so a list that still holds
        # it does not reopen the music into the same refusal. Cleared when
        # the device leaves the list or the listener chooses again.
        self._refused_identity = ""
        self._refusal: Refusal | None = None

    @property
    def output_choice(self) -> OutputChoice:
        """What the listener last chose."""
        return self._choice

    @property
    def device_in_use(self) -> OutputDevice | None:
        """Where streams open now; None is the system default."""
        return self._in_use

    @property
    def output_entries(self) -> tuple[OutputEntry, ...]:
        """The list the window shows."""
        return output_list(self._outputs, self._choice, self._in_use)

    @property
    def output_missing(self) -> bool:
        """Whether a named choice has no device listed for it. FR-O10."""
        return (
            not self._choice.follows_default
            and device_in_use(self._outputs, self._choice) is None
        )

    def take_refusal(self) -> Refusal | None:
        """The last refusal, once; None after it has been taken."""
        refusal, self._refusal = self._refusal, None
        return refusal

    def choose_output(self, choice: OutputChoice) -> None:
        """Send the music to this device from now on. FR-O07.

        The track in hand moves at once, where it is and as it was, since a
        choice heard only on the next track reads as one that did nothing.
        Choosing again is asking again, so a refusal is forgotten.
        """
        if choice == self._choice and not self._refused_identity:
            return
        self._choice = choice
        self._refused_identity = ""
        self._move_to(device_in_use(self._outputs, choice))

    def outputs_listed(self, devices: tuple[OutputDevice, ...]) -> OutputChange:
        """Take the system's list of devices again. FR-O13.

        Ruled by Oliver on 2026-09-18 (OQ-O5), the rule of 2026-09-14 governs
        the track in hand: music never goes to the speakers without a press.
        Losing the chosen device pauses it where it was, exactly as a move of
        the system's output does; play then opens it on the default (FR-O11).
        The device coming back takes the track in hand where it is and as it
        was, so a pause is still a pause (FR-O12).
        """
        self._outputs = devices
        listed = device_in_use(devices, self._choice)
        if listed is None:
            self._refused_identity = ""
        elif listed.identity == self._refused_identity:
            listed = None
        if listed == self._in_use:
            return OutputChange.NONE
        self._in_use = listed
        self._player.use_device(listed)
        if listed is None:
            self.output_moved()
            return OutputChange.LOST
        if self._player.state.is_active:
            self._reopen_in_place()
        return OutputChange.RETURNED

    def _move_to(self, device: OutputDevice | None) -> None:
        """Open later streams on `device`; reopen what is loaded there."""
        if device == self._in_use:
            return
        self._in_use = device
        self._player.use_device(device)
        if self._player.state.is_active:
            self._reopen_in_place()

    def _open(self, source: TrackSource, request: OutputRequest) -> None:
        """Load `source`; on the system default if the device refuses. FR-O08.

        The default refusing leaves nothing to fall back to, so that raises
        as any failure to open does.
        """
        try:
            self._player.load(source, request)
        except OutputRefused as refused:
            device = self._in_use
            if device is None:
                raise
            self._refusal = Refusal(device=device, reason=str(refused))
            self._refused_identity = device.identity
            self._in_use = None
            self._player.use_device(None)
            self._player.load(source, request)
