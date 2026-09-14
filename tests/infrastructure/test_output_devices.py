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
    rescan,
)

HEADPHONES = b"headphones"
SPEAKERS = b"speakers"
ANSWER = ("stream", "report", "dtype")
REQUEST = "request"


@pytest.fixture(scope="module")
def application() -> QApplication:
    """One real QApplication, since these are Qt objects. Qt is never mocked."""
    existing = QApplication.instance()
    return existing or QApplication([])


class Machine:
    """The default device, plus a record of what was done about it."""

    def __init__(self) -> None:
        self.default = HEADPHONES
        self.events: list[object] = []
        self.moves = 0

    def refresh(self) -> None:
        self.events.append("rescan")

    def opener(self, request, device):
        self.events.append((request, device))
        return ANSWER

    def watching(self) -> OutputDevices:
        devices = OutputDevices(
            opener=self.opener, refresh=self.refresh, default_id=lambda: self.default
        )
        devices.changed.connect(self._moved)
        return devices

    def _moved(self) -> None:
        self.moves += 1


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


class TestTheRealHalves:
    def test_qt_names_the_default_by_identity(self, application) -> None:
        assert isinstance(default_output_id(), bytes)

    def test_portaudio_answers_after_being_taken_again(self) -> None:
        rescan()
        assert sounddevice.query_hostapis()
