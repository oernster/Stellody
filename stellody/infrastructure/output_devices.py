"""Noticing that the system has moved its sound output somewhere else.

Two things were measured on the reference machine on 2026-09-14, with
headphones connected after Stellody had started:

- PortAudio lists the devices once, when it starts. A process left running
  went on naming the headphones as the default for as long as it ran, while a
  brand new process named the speakers the moment Windows switched. Asking
  PortAudio for its default on every stream is therefore not enough by itself;
  its list has to be taken again first.
- Qt does notice. `QMediaDevices.audioOutputsChanged` fired within a second of
  every switch, in both directions, though twice for each one. It also fires
  for a change to the device LIST, which need not move the default at all.

So a move is reported only when the default device's identity differs from the
last one seen. That turns two signals into one; a device arriving that is not
the default turns into none.

Taking the list again closes every stream PortAudio has open, so it is done
only where none is: on the way into opening a stream, which the engine reaches
once the previous stream is closed; or when the window asks which rates the new
device takes exclusively while nothing is loaded.
"""

from __future__ import annotations

from collections.abc import Callable

import sounddevice
from PySide6.QtCore import QObject, Signal, Slot
from PySide6.QtMultimedia import QMediaDevices

from stellody.domain.playback import OutputReport, OutputRequest
from stellody.infrastructure.audio import Opener
from stellody.infrastructure.output import exclusive_rates, open_output


def rescan() -> None:
    """Have PortAudio list the devices again, closing any stream it holds."""
    sounddevice._terminate()
    sounddevice._initialize()


def default_output_id() -> bytes:
    """The identity of the system's default output device, as Qt knows it."""
    return bytes(QMediaDevices.defaultAudioOutput().id().data())


class OutputDevices(QObject):
    """Says when the default output moves; opens the next stream where it went."""

    changed = Signal()

    def __init__(
        self,
        opener: Opener = open_output,
        refresh: Callable[[], None] = rescan,
        default_id: Callable[[], bytes] = default_output_id,
        parent: QObject | None = None,
        rates: Callable[[int | None], tuple[int, ...] | None] = exclusive_rates,
    ) -> None:
        super().__init__(parent)
        self._opener = opener
        self._refresh = refresh
        self._default_id = default_id
        self._rates = rates
        self._known = default_id()
        # Whether a move has been seen since PortAudio's list was last taken.
        self._moved = False
        # The last answer about exclusive rates, with the device it was about;
        # None until asked and again after every move.
        self._answered: tuple[int | None, tuple[int, ...] | None] | None = None
        self._devices = QMediaDevices(self)
        self._devices.audioOutputsChanged.connect(self.notice)

    @Slot()
    def notice(self) -> None:
        """Report a move of the default output once; anything else is not one."""
        now = self._default_id()
        if now == self._known:
            return
        self._known = now
        self._moved = True
        self.changed.emit()

    def open_output(
        self, request: OutputRequest, device: int | None = None
    ) -> tuple[sounddevice.OutputStream, OutputReport, str]:
        """Open a stream, taking PortAudio's list again first after a move."""
        self._take_the_list_again()
        return self._opener(request, device)

    def exclusive_rates(
        self, device: int | None, stream_open: bool
    ) -> tuple[int, ...] | None:
        """Which rates the device takes exclusively, kept until the output moves.

        Each answer is six questions to the driver while the window asks four
        times a second, so it is kept. After a move the list is taken again
        first, since until then PortAudio still means the old device; that
        closes any stream open, so with one open the answer is None, unknown,
        until the next stream opens and takes the list itself. Unknown stands
        nothing down, which is the safe direction to be wrong in.
        """
        if self._moved and stream_open:
            return None
        self._take_the_list_again()
        if self._answered is None or self._answered[0] != device:
            self._answered = (device, self._rates(device))
        return self._answered[1]

    def _take_the_list_again(self) -> None:
        """Have PortAudio list the devices again, where a move says it must."""
        if self._moved:
            self._refresh()
            self._moved = False
            self._answered = None
