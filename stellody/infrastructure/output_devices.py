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
the default turns into none. Each move says whether the default it left has
left the list as well: a device arriving carries the music on, one leaving
pauses it (`OUTPUTS.md` Amendment 5).

A change to the list itself is reported separately (`listed`), once for each
different set of devices, so the output list a listener chooses from is kept
current with no relaunch (`OUTPUTS.md` FR-O13). Either kind of change leaves
PortAudio's list out of date, since PortAudio knows only what it listed when it
last looked: a device connected since then cannot be opened until it looks
again.

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

from stellody.domain.outputs import OutputDevice
from stellody.domain.playback import OutputReport, OutputRequest
from stellody.infrastructure.output_list import NamedOpener, named_rates, open_named


def rescan() -> None:
    """Have PortAudio list the devices again, closing any stream it holds."""
    sounddevice._terminate()
    sounddevice._initialize()


def default_output_id() -> bytes:
    """The identity of the system's default output device, as Qt knows it."""
    return bytes(QMediaDevices.defaultAudioOutput().id().data())


def output_ids() -> tuple[bytes, ...]:
    """The identity of every output device, as Qt lists them."""
    return tuple(bytes(device.id().data()) for device in QMediaDevices.audioOutputs())


class OutputDevices(QObject):
    """Says when the outputs change; opens the next stream where they went."""

    # True when the default left behind is no longer listed.
    changed = Signal(bool)
    listed = Signal()

    def __init__(
        self,
        opener: NamedOpener = open_named,
        refresh: Callable[[], None] = rescan,
        default_id: Callable[[], bytes] = default_output_id,
        parent: QObject | None = None,
        rates: Callable[[OutputDevice | None], tuple[int, ...] | None] = named_rates,
        output_ids: Callable[[], tuple[bytes, ...]] = output_ids,
    ) -> None:
        super().__init__(parent)
        self._opener = opener
        self._refresh = refresh
        self._default_id = default_id
        self._rates = rates
        self._output_ids = output_ids
        self._known = default_id()
        self._known_list = output_ids()
        # Whether anything has changed since PortAudio's list was last taken.
        self._moved = False
        # The last answer about exclusive rates, with the device it was about;
        # None until asked and again after every change.
        self._answered: tuple[OutputDevice | None, tuple[int, ...] | None] | None = None
        self._devices = QMediaDevices(self)
        self._devices.audioOutputsChanged.connect(self.notice)

    @Slot()
    def notice(self) -> None:
        """Report each different change once: the default moving, the list."""
        listing = self._output_ids()
        if listing != self._known_list:
            self._known_list = listing
            self._moved = True
            self.listed.emit()
        now = self._default_id()
        if now == self._known:
            return
        left = self._known not in listing
        self._known = now
        self._moved = True
        self.changed.emit(left)

    def open_output(
        self, request: OutputRequest, device: OutputDevice | None = None
    ) -> tuple[sounddevice.OutputStream, OutputReport, str]:
        """Open a stream, taking PortAudio's list again first after a move."""
        self._take_the_list_again()
        return self._opener(request, device)

    def exclusive_rates(
        self, device: OutputDevice | None, stream_open: bool
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
