"""Noticing a move of the default output, then opening the next stream there.

The measurements behind this are in the module's own docstring: PortAudio keeps
the device list it started with, while Qt signals every switch, twice. What a
machine without anybody switching devices can still assert is the rule laid
over those two facts, driven here through stand-ins for the identity Qt reports,
for the rescan and for the opener.
"""

from __future__ import annotations

import pytest
import sounddevice
from PySide6.QtWidgets import QApplication

from stellody.infrastructure.output_devices import (
    OutputDevices,
    default_output_id,
    output_ids,
    rescan,
)

HEADPHONES = b"headphones"
SPEAKERS = b"speakers"
BATHYS = b"bathys"
ANSWER = ("stream", "report", "dtype")
REQUEST = "request"
# What each device takes exclusively, as the Bathys and the speakers answered
# on 2026-09-18.
RATES = {HEADPHONES: (48000,), SPEAKERS: (44100, 48000, 96000, 192000)}
NO_STREAM = False
A_STREAM = True


class Machine:
    """The default device, plus a record of what was done about it."""

    def __init__(self) -> None:
        self.default = HEADPHONES
        self.outputs = (HEADPHONES, SPEAKERS)
        self.events: list[object] = []
        self.moves = 0
        self.listings = 0

    def refresh(self) -> None:
        self.events.append("rescan")

    def opener(self, request, device):
        self.events.append((request, device))
        return ANSWER

    def rates(self, device):
        """The driver being asked, which costs a question a rate."""
        self.events.append(("rates", device))
        return RATES[self.default]

    def watching(self) -> OutputDevices:
        devices = OutputDevices(
            opener=self.opener,
            refresh=self.refresh,
            default_id=lambda: self.default,
            rates=self.rates,
            output_ids=lambda: self.outputs,
        )
        devices.changed.connect(self._moved)
        devices.listed.connect(self._listed)
        return devices

    def _moved(self) -> None:
        self.moves += 1

    def _listed(self) -> None:
        self.listings += 1


@pytest.fixture
def machine(application: QApplication) -> Machine:
    return Machine()


class TestNoticingAMove:
    def test_a_move_of_the_default_is_reported(self, machine) -> None:
        devices = machine.watching()
        machine.default = SPEAKERS
        devices.notice()
        assert machine.moves == 1

    def test_the_second_signal_for_one_switch_is_not_another_move(
        self, machine
    ) -> None:
        """Measured: Qt signals twice for every switch."""
        devices = machine.watching()
        machine.default = SPEAKERS
        devices.notice()
        devices.notice()
        assert machine.moves == 1

    def test_a_list_change_that_leaves_the_default_is_not_a_move(self, machine) -> None:
        devices = machine.watching()
        devices.notice()
        assert machine.moves == 0

    def test_moving_back_is_a_move_too(self, machine) -> None:
        devices = machine.watching()
        machine.default = SPEAKERS
        devices.notice()
        machine.default = HEADPHONES
        devices.notice()
        assert machine.moves == 2


class TestNoticingTheListChange:
    """FR-O13: the Bathys connecting while Stellody runs is offered at once."""

    def test_a_device_connecting_is_announced(self, machine) -> None:
        devices = machine.watching()
        machine.outputs = (*machine.outputs, BATHYS)
        devices.notice()
        assert machine.listings == 1
        assert machine.moves == 0

    def test_the_same_list_twice_is_announced_once(self, machine) -> None:
        """Qt signals more than once for one change; one answer is enough."""
        devices = machine.watching()
        machine.outputs = (*machine.outputs, BATHYS)
        devices.notice()
        devices.notice()
        assert machine.listings == 1

    def test_a_device_leaving_is_announced(self, machine) -> None:
        devices = machine.watching()
        machine.outputs = (HEADPHONES,)
        devices.notice()
        assert machine.listings == 1

    def test_the_next_stream_takes_portaudios_list_again(self, machine) -> None:
        """PortAudio knows only the devices it listed; the new one needs it."""
        devices = machine.watching()
        machine.outputs = (*machine.outputs, BATHYS)
        devices.notice()
        devices.open_output(REQUEST, BATHYS)
        assert machine.events == ["rescan", (REQUEST, BATHYS)]


class TestOpeningAfterAMove:
    def test_the_list_is_taken_again_before_the_stream_opens(self, machine) -> None:
        devices = machine.watching()
        machine.default = SPEAKERS
        devices.notice()
        assert devices.open_output(REQUEST) == ANSWER
        assert machine.events == ["rescan", (REQUEST, None)]

    def test_only_the_first_stream_after_a_move_pays_for_it(self, machine) -> None:
        devices = machine.watching()
        machine.default = SPEAKERS
        devices.notice()
        devices.open_output(REQUEST)
        devices.open_output(REQUEST, 3)
        assert machine.events == ["rescan", (REQUEST, None), (REQUEST, 3)]

    def test_with_no_move_nothing_is_taken_again(self, machine) -> None:
        devices = machine.watching()
        devices.open_output(REQUEST)
        assert machine.events == [(REQUEST, None)]


class TestAskingWhichRatesTheDeviceTakes:
    """Asked on every refresh of the window, so it must cost nothing twice.

    Each answer is six questions to the driver; the window asks four times a
    second. So an answer is kept until the output moves. After a move the list
    has to be taken again before the answer means the new device, which closes
    any stream open, so that is done only while none is; with one open the
    answer is unknown until the next stream opens, which takes the list anyway.
    """

    def test_an_answer_is_kept_rather_than_asked_again(self, machine) -> None:
        devices = machine.watching()
        assert devices.exclusive_rates(None, NO_STREAM) == RATES[HEADPHONES]
        assert devices.exclusive_rates(None, NO_STREAM) == RATES[HEADPHONES]
        assert machine.events == [("rates", None)]

    def test_a_move_with_no_stream_open_asks_the_new_device(self, machine) -> None:
        devices = machine.watching()
        devices.exclusive_rates(None, NO_STREAM)
        machine.default = SPEAKERS
        devices.notice()
        assert devices.exclusive_rates(None, NO_STREAM) == RATES[SPEAKERS]
        assert machine.events == [("rates", None), "rescan", ("rates", None)]

    def test_a_move_with_a_stream_open_answers_unknown(self, machine) -> None:
        """Taking the list again would close the stream the music is on."""
        devices = machine.watching()
        machine.default = SPEAKERS
        devices.notice()
        assert devices.exclusive_rates(None, A_STREAM) is None
        assert "rescan" not in machine.events

    def test_the_next_stream_brings_the_answer_back(self, machine) -> None:
        devices = machine.watching()
        machine.default = SPEAKERS
        devices.notice()
        devices.exclusive_rates(None, A_STREAM)
        devices.open_output(REQUEST)
        assert devices.exclusive_rates(None, A_STREAM) == RATES[SPEAKERS]
        assert machine.events.count("rescan") == 1

    def test_another_device_is_asked_about_afresh(self, machine) -> None:
        devices = machine.watching()
        devices.exclusive_rates(None, NO_STREAM)
        devices.exclusive_rates(3, NO_STREAM)
        assert machine.events == [("rates", None), ("rates", 3)]


class TestTheRealHalves:
    def test_qt_names_the_default_by_identity(self, application) -> None:
        assert isinstance(default_output_id(), bytes)

    def test_qt_lists_every_output_by_identity_with_the_default_among_them(
        self, application
    ) -> None:
        assert default_output_id() in output_ids()

    def test_portaudio_answers_after_being_taken_again(self) -> None:
        rescan()
        assert sounddevice.query_hostapis()
