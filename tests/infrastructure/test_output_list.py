"""Which output devices there are; which PortAudio device each one is.

`OUTPUTS.md` FR-O04, FR-O05, FR-O08, FR-O13 and NFR-O-PERF-002. The real
halves are asked on this machine, read only: nothing is opened or played. The
refusals and the other platforms' route are driven through stand-ins, since
this machine cannot be made to lose a device or to be a Mac.
"""

from __future__ import annotations

import ctypes
import threading

import pytest
import sounddevice

from stellody.application.playback_ports import OutputRefused
from stellody.domain.outputs import OutputDevice
from stellody.domain.playback import OutputMode, OutputRequest
from stellody.domain.track import CD_BIT_DEPTH, CD_SAMPLE_RATE
from stellody.infrastructure import endpoints, output, output_list
from stellody.infrastructure.output_devices import OutputDevices
from stellody.infrastructure.portaudio import OutputUnavailableError

pytestmark = pytest.mark.skipif(
    output.sys.platform != output.WINDOWS, reason="asks Windows' own list"
)

REQUEST = OutputRequest(
    sample_rate=CD_SAMPLE_RATE, bit_depth=CD_BIT_DEPTH, mode=OutputMode.SHARED
)
NOWHERE = OutputDevice(identity="{nowhere}", name="A device nobody has")
ANSWER = ("stream", "report", "dtype")
# E_FAIL: any COM failure other than the thread already having COM.
OTHER_COM_FAILURE = -2147467259
# COINIT_MULTITHREADED, the other way a thread's COM can be set up.
MULTITHREADED = 0


def _wasapi_inputs_only() -> set[str]:
    """Names PortAudio's WASAPI lists as capture devices and nothing else."""
    apis = sounddevice.query_hostapis()
    return {
        device["name"]
        for device in sounddevice.query_devices()
        if apis[device["hostapi"]]["name"] == output_list.WASAPI
        and device["max_output_channels"] == 0
    }


class TestTheRealList:
    def test_the_list_is_read_from_the_outputs_alone(self) -> None:
        """FR-O04: no microphone, line input or loopback appears."""
        names = {device.name for device in output_list.listed_outputs()}
        assert names
        assert not names & _wasapi_inputs_only()

    def test_every_listed_device_is_one_portaudio_can_open(self) -> None:
        """Amendment 2: each is found, under its own name, as an output."""
        known = dict(output_list.portaudio_outputs())
        for device in output_list.listed_outputs():
            assert known[output_list.portaudio_number(device)] == device.name

    def test_namesakes_are_different_devices(self) -> None:
        """Measured: two monitors here share one name; they stay two."""
        listed = output_list.listed_outputs()
        numbers = {output_list.portaudio_number(device) for device in listed}
        assert len(numbers) == len(listed)

    def test_a_thread_without_com_gets_the_same_list(self) -> None:
        """COM is set up for a thread that lacks it, then taken down."""
        answers: list[tuple[OutputDevice, ...]] = []
        worker = threading.Thread(
            target=lambda: answers.append(endpoints.render_endpoints())
        )
        worker.start()
        worker.join()
        assert answers == [endpoints.render_endpoints()]

    def test_a_thread_whose_com_is_set_up_another_way_is_left_so(self) -> None:
        """As Qt's thread is: it can use COM however it was set up."""
        answers: list[tuple[OutputDevice, ...]] = []

        def asked_from_a_multithreaded_apartment() -> None:
            ctypes.oledll.ole32.CoInitializeEx(None, MULTITHREADED)
            try:
                answers.append(endpoints.render_endpoints())
            finally:
                ctypes.windll.ole32.CoUninitialize()

        worker = threading.Thread(target=asked_from_a_multithreaded_apartment)
        worker.start()
        worker.join()
        assert answers == [endpoints.render_endpoints()]


class TestWhenWindowsCannotBeAsked:
    def test_another_com_failure_is_raised(self, monkeypatch) -> None:
        """Only the thread already having COM is not a fault."""

        def refuses(*_args) -> None:
            raise OSError(0, "refused", None, OTHER_COM_FAILURE)

        monkeypatch.setattr(ctypes.oledll.ole32, "CoInitializeEx", refuses)
        with pytest.raises(OSError):
            endpoints.render_endpoints()

    def test_the_list_falls_back_to_qts(self, monkeypatch, application) -> None:
        def fails() -> tuple[OutputDevice, ...]:
            raise OSError("no enumerator")

        monkeypatch.setattr(endpoints, "render_endpoints", fails)
        assert output_list.listed_outputs() == output_list.qt_outputs()


class TestAnotherPlatform:
    def test_qts_list_is_used(self, monkeypatch, application) -> None:
        monkeypatch.setattr(output_list.sys, "platform", "linux")
        assert output_list.listed_outputs() == output_list.qt_outputs()

    def test_portaudios_own_default_host_api_is_the_one_matched(
        self, monkeypatch
    ) -> None:
        default_api = sounddevice.query_devices(kind="output")["hostapi"]
        monkeypatch.setattr(output_list.sys, "platform", "linux")
        devices = sounddevice.query_devices()
        for number, _name in output_list.portaudio_outputs():
            assert devices[number]["hostapi"] == default_api


class TestFindingADevice:
    def test_a_device_nobody_lists_is_refused(self) -> None:
        """FR-O08 starts here: what cannot be found cannot be opened."""
        with pytest.raises(OutputRefused, match=NOWHERE.name):
            output_list.portaudio_number(NOWHERE)


class TestOpening:
    def _opened(self, monkeypatch) -> list[object]:
        calls: list[object] = []

        def opener(request, number):
            calls.append(number)
            return ANSWER

        monkeypatch.setattr(output, "open_output", opener)
        return calls

    def test_the_default_opens_as_it_always_did(self, monkeypatch) -> None:
        calls = self._opened(monkeypatch)
        assert output_list.open_named(REQUEST) == ANSWER
        assert calls == [None]

    def test_a_named_device_opens_by_its_number(self, monkeypatch) -> None:
        calls = self._opened(monkeypatch)
        device = output_list.listed_outputs()[0]
        output_list.open_named(REQUEST, device)
        assert calls == [output_list.portaudio_number(device)]

    def test_a_named_device_that_will_not_open_is_refused(self, monkeypatch) -> None:
        """FR-O08: the device's own reason is what the window says."""

        def unavailable(request, number):
            raise OutputUnavailableError("held by another application")

        monkeypatch.setattr(output, "open_output", unavailable)
        with pytest.raises(OutputRefused, match="held by another application"):
            output_list.open_named(REQUEST, output_list.listed_outputs()[0])


class TestAskingTheRates:
    def _asked(self, monkeypatch) -> list[object]:
        asked: list[object] = []

        def rates(number):
            asked.append(number)
            return (CD_SAMPLE_RATE,)

        monkeypatch.setattr(output, "exclusive_rates", rates)
        return asked

    def test_the_default_is_asked_as_it_always_was(self, monkeypatch) -> None:
        asked = self._asked(monkeypatch)
        assert output_list.named_rates(None) == (CD_SAMPLE_RATE,)
        assert asked == [None]

    def test_a_named_device_is_asked_by_its_number(self, monkeypatch) -> None:
        asked = self._asked(monkeypatch)
        device = output_list.listed_outputs()[0]
        output_list.named_rates(device)
        assert asked == [output_list.portaudio_number(device)]

    def test_a_device_that_cannot_be_found_is_unknown(self, monkeypatch) -> None:
        """Unknown stands nothing down, the safe direction to be wrong in."""
        asked = self._asked(monkeypatch)
        assert output_list.named_rates(NOWHERE) is None
        assert asked == []


def test_a_list_change_leaves_the_stream_alone(application) -> None:
    """NFR-O-PERF-002: noticing a new device takes nothing from PortAudio.

    PortAudio's list is taken again only on the way into the next stream,
    since taking it closes whatever stream is open.
    """
    outputs = [(b"speakers",)]
    rescans: list[str] = []
    devices = OutputDevices(
        opener=lambda request, device: ANSWER,
        refresh=lambda: rescans.append("rescan"),
        default_id=lambda: b"speakers",
        rates=lambda device: None,
        output_ids=lambda: outputs[0],
    )
    outputs[0] = (b"speakers", b"bathys")
    devices.notice()
    assert rescans == []
    devices.open_output(REQUEST)
    assert rescans == ["rescan"]
