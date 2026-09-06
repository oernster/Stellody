"""The output every platform has; the one thing it must never do.

Stellody reached its device through WASAPI alone, which exists on Windows and
nowhere else. The substrate underneath it is PortAudio, which exists
everywhere, so what is asserted here is that the portable path opens a stream
without asking for anything Windows owns and reports honestly what it opened.

The device is stood in for. What is being measured is the ASKING: which
arguments reach sounddevice and what is said about the stream afterwards.
Nothing here makes a sound, so it runs on a machine with no audio hardware at
all, which is what the Linux and macOS work needs of it.
"""

from __future__ import annotations

import pytest

from stellody.domain.playback import OutputMode, OutputRequest
from stellody.infrastructure import portaudio

RATE = 44100
CHANNELS = 2
DEPTH = 16


class FakeStream:
    """Stands in for the stream sounddevice hands back."""


def asked(monkeypatch: pytest.MonkeyPatch) -> dict:
    """Record what sounddevice was asked for, answering with a fake stream."""
    seen: dict = {}

    def open_stream(**kwargs):
        seen.update(kwargs)
        return FakeStream()

    monkeypatch.setattr(portaudio.sounddevice, "OutputStream", open_stream)
    return seen


def a_request(mode: OutputMode) -> OutputRequest:
    return OutputRequest(
        sample_rate=RATE, bit_depth=DEPTH, channels=CHANNELS, mode=mode
    )


class TestWhatIsAskedFor:
    def test_no_host_api_settings_are_passed_at_all(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The load-bearing one.

        A settings object belongs to one host API. Handing a WASAPI object to
        CoreAudio or to ALSA is the same fault the Windows module records in
        reverse; it fails the stream outright rather than degrading, so
        the absence is asserted rather than assumed.
        """
        seen = asked(monkeypatch)
        portaudio.open_output(a_request(OutputMode.SHARED))
        assert "extra_settings" not in seen

    def test_the_track_rate_and_channels_are_what_is_requested(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        seen = asked(monkeypatch)
        portaudio.open_output(a_request(OutputMode.SHARED))
        assert seen["samplerate"] == RATE
        assert seen["channels"] == CHANNELS
        assert seen["dtype"] == portaudio.SHARED_DTYPE

    def test_no_device_is_named_so_portaudio_chooses(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Nothing is asked for by name here, so there is nothing to resolve."""
        seen = asked(monkeypatch)
        portaudio.open_output(a_request(OutputMode.SHARED))
        assert seen["device"] is None
        assert portaudio.default_device() is None

    def test_a_named_device_is_honoured(self, monkeypatch: pytest.MonkeyPatch) -> None:
        seen = asked(monkeypatch)
        portaudio.open_output(a_request(OutputMode.SHARED), device=7)
        assert seen["device"] == 7


class TestWhatIsReported:
    def test_a_mixer_request_is_answered_with_no_reason(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """An empty reason means the mixer was wanted rather than left over."""
        asked(monkeypatch)
        _stream, report, dtype = portaudio.open_output(a_request(OutputMode.SHARED))
        assert report.mode is OutputMode.SHARED
        assert report.fallback_reason == ""
        assert dtype == portaudio.SHARED_DTYPE

    def test_asking_for_exclusive_says_why_it_did_not_happen(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Silently ignoring the ask would leave the report claiming too much."""
        asked(monkeypatch)
        _stream, report, _dtype = portaudio.open_output(a_request(OutputMode.EXCLUSIVE))
        assert report.mode is OutputMode.SHARED
        assert report.fallback_reason == portaudio.NO_EXCLUSIVE_HERE

    def test_nothing_here_is_ever_called_bit_perfect(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The promise the application leads with, held where it cannot hold."""
        asked(monkeypatch)
        _stream, report, _dtype = portaudio.open_output(a_request(OutputMode.EXCLUSIVE))
        assert not report.is_bit_perfect

    def test_the_depth_reported_is_the_mixer_s_own(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """What reaches the hardware is the mixer's depth, not the file's."""
        asked(monkeypatch)
        _stream, report, _dtype = portaudio.open_output(a_request(OutputMode.SHARED))
        assert report.bit_depth == portaudio.MIXER_BIT_DEPTH


def test_a_machine_with_no_output_at_all_says_so(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Reported rather than swallowed: silence is indistinguishable from a bug."""

    def refuse(**_kwargs):
        raise OSError("no device")

    monkeypatch.setattr(portaudio.sounddevice, "OutputStream", refuse)
    with pytest.raises(portaudio.OutputUnavailableError) as raised:
        portaudio.open_output(a_request(OutputMode.SHARED))
    assert str(RATE) in str(raised.value)
