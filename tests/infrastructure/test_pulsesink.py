"""Addressing one sound server sink, which is how Linux reaches a device.

`OUTPUTS.md` Amendment 6. The route itself is asked of this machine where it
is a Linux one, read only: nothing is opened and nothing is played. The
platform rule and the refusal are driven through stand-ins, since this machine
cannot be made to be a Mac nor to lose its sound server.
"""

from __future__ import annotations

import os

import pytest
from PySide6.QtWidgets import QApplication

from stellody.domain.outputs import OutputDevice
from stellody.domain.playback import OutputMode, OutputRequest
from stellody.domain.track import CD_BIT_DEPTH, CD_SAMPLE_RATE
from stellody.infrastructure import output, output_list, pulsesink

REQUEST = OutputRequest(
    sample_rate=CD_SAMPLE_RATE, bit_depth=CD_BIT_DEPTH, mode=OutputMode.SHARED
)
SINK = OutputDevice(identity="bluez_output.AA_BB", name="Some headphones")
NAMELESS = OutputDevice(identity="", name="A device with no identity")
ANSWER = ("stream", "report", "dtype")
PULSE_NUMBER = 7


class TestWhichPlatformsRouteBySink:
    def test_windows_and_macos_find_the_device_in_the_list(self) -> None:
        """Both hand PortAudio a list a listener's own names appear in."""
        assert not pulsesink.routes_by_sink(output.WINDOWS)
        assert not pulsesink.routes_by_sink(output.MACOS)

    def test_anything_else_names_a_sink(self) -> None:
        """Linux and any platform nobody has thought about yet."""
        assert pulsesink.routes_by_sink("linux")

    def test_the_platform_is_this_one_when_none_is_named(self) -> None:
        assert pulsesink.routes_by_sink() == (
            output.sys.platform not in (output.WINDOWS, output.MACOS)
        )


class TestWhichDeviceAddressesASink:
    def test_a_device_without_identity_names_no_sink(self) -> None:
        """Nothing to name means the by-name match is the only route left."""
        assert pulsesink.sink_route(NAMELESS, "linux") is None

    def test_windows_never_takes_this_route(self) -> None:
        assert pulsesink.sink_route(SINK, output.WINDOWS) is None

    def test_a_machine_with_no_sound_server_takes_the_other_route(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """ALSA alone names the hardware, so there is a name to match."""
        monkeypatch.setattr(pulsesink, "pulse_device", lambda: None)
        assert pulsesink.sink_route(SINK, "linux") is None

    def test_the_sound_server_is_what_a_sink_is_named_to(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(pulsesink, "pulse_device", lambda: PULSE_NUMBER)
        assert pulsesink.sink_route(SINK, "linux") == PULSE_NUMBER


class TestHoldingTheChosenSink:
    def test_the_sink_is_named_for_the_open_alone(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv(pulsesink.SINK_VARIABLE, raising=False)
        with pulsesink.chosen_sink(SINK.identity):
            assert os.environ[pulsesink.SINK_VARIABLE] == SINK.identity
        assert pulsesink.SINK_VARIABLE not in os.environ

    def test_what_was_there_before_is_put_back(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv(pulsesink.SINK_VARIABLE, "somebody_elses_sink")
        with pulsesink.chosen_sink(SINK.identity):
            assert os.environ[pulsesink.SINK_VARIABLE] == SINK.identity
        assert os.environ[pulsesink.SINK_VARIABLE] == "somebody_elses_sink"

    def test_a_failed_open_puts_it_back_too(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv(pulsesink.SINK_VARIABLE, raising=False)
        with pytest.raises(RuntimeError), pulsesink.chosen_sink(SINK.identity):
            raise RuntimeError("the stream would not open")
        assert pulsesink.SINK_VARIABLE not in os.environ


class TestOpeningOnASink:
    def test_the_stream_is_opened_on_the_sound_server_naming_the_sink(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Amendment 6: the device is addressed rather than matched."""
        seen: dict[str, object] = {}

        def _open(request: OutputRequest, number: int | None) -> tuple[str, ...]:
            seen["number"] = number
            seen["sink"] = os.environ.get(pulsesink.SINK_VARIABLE)
            return ANSWER

        monkeypatch.setattr(pulsesink, "sink_route", lambda device: PULSE_NUMBER)
        monkeypatch.setattr(output, "open_output", _open)
        assert output_list.open_named(REQUEST, SINK) == ANSWER
        assert seen == {"number": PULSE_NUMBER, "sink": SINK.identity}

    def test_the_rates_question_is_asked_of_the_sound_server(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """No device number is matched where none can be."""
        monkeypatch.setattr(pulsesink, "sink_route", lambda device: PULSE_NUMBER)
        monkeypatch.setattr(output, "exclusive_rates", lambda number: (number,))
        assert output_list.named_rates(SINK) == (PULSE_NUMBER,)


@pytest.mark.skipif(
    output.sys.platform in (output.WINDOWS, output.MACOS),
    reason="asks this machine's own sound server",
)
class TestThisMachine:
    def test_every_listed_device_can_be_addressed(
        self, application: QApplication
    ) -> None:
        """FR-O08 read the other way: nothing a listener sees is refused.

        Skipped rather than failed on a machine running no sound server,
        which is the case the by-name route is still there for.
        """
        if pulsesink.pulse_device() is None:
            pytest.skip("no sound server on this machine")
        devices = output_list.listed_outputs()
        assert devices
        for device in devices:
            assert pulsesink.sink_route(device) is not None
