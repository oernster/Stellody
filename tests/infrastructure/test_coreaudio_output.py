"""What a Mac is asked for; what is honestly claimed about the answer.

The device is stood in for. What is measured is the ASKING: which arguments
reach sounddevice and what is said about the stream afterwards. Nothing here
makes a sound, so it runs on a machine with no audio hardware at all, which is
what this work needs of it: there is no Mac to run it on.

**That absence is the point of this file.** The CoreAudio path cannot be heard
here, so every claim it makes has to be pinned by assertion instead. The flags
were read off the built library on 2026-09-17 rather than taken from a manual.
`paMacCorePro` turned out to be 0x1, exactly
`paMacCoreChangeDeviceParameters`: PortAudio has no hog mode, so nothing here
may claim to have taken the device away from anything else.
"""

from __future__ import annotations

import inspect

import pytest

from stellody.domain.playback import OutputMode, OutputRequest
from stellody.infrastructure import coreaudio

RATE = 96000
CHANNELS = 2
DEPTH = 24
NO_DEPTH = 0


class FakeStream:
    """Stands in for the stream sounddevice hands back."""


class FakeSettings:
    """Stands in for CoreAudioSettings, which cannot be built off a Mac.

    `PaMacCore_SetupStreamInfo` is absent from the Windows build of PortAudio,
    measured on 2026-09-17: constructing the real settings object here raises
    before any device is consulted. So the settings are the seam; what is
    asserted is the flags the module asks for rather than the struct.
    """

    def __init__(self) -> None:
        self.flags = dict.fromkeys(coreaudio.DIRECT_FLAGS, True)


def asked(monkeypatch: pytest.MonkeyPatch, refuse: bool = False) -> dict:
    """Record what sounddevice was asked for, answering with a fake stream."""
    seen: dict = {}

    def open_stream(**kwargs):
        seen.setdefault("attempts", []).append(kwargs)
        settings = kwargs.get("extra_settings")
        if refuse and settings is not None:
            raise RuntimeError("the device will not run at that rate")
        return FakeStream()

    monkeypatch.setattr(coreaudio.sounddevice, "OutputStream", open_stream)
    monkeypatch.setattr(coreaudio, "default_device", lambda: None)
    monkeypatch.setattr(coreaudio, "direct_settings", FakeSettings)
    return seen


def request(mode: OutputMode, depth: int = DEPTH) -> OutputRequest:
    """One track's worth of asking."""
    return OutputRequest(
        sample_rate=RATE, bit_depth=depth, mode=mode, channels=CHANNELS
    )


class TestAskingForTheDeviceUntouched:
    def test_the_two_flags_that_refuse_conversion_are_both_named(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Either one alone converts: the rate changes; else the stream fails."""
        seen = asked(monkeypatch)
        coreaudio.open_output(request(OutputMode.EXCLUSIVE))
        settings = seen["attempts"][0]["extra_settings"]
        assert settings.flags == {
            "change_device_parameters": True,
            "fail_if_conversion_required": True,
        }

    def test_those_flag_names_are_ones_sounddevice_actually_takes(self) -> None:
        """Guard the guard: names asserted against a fake prove nothing alone.

        The settings object cannot be built here, so the NAMES are checked
        against the real signature instead. A sounddevice that renamed one
        would otherwise leave the fake agreeing with a module that raises on
        every Mac.
        """
        taken = inspect.signature(
            coreaudio.sounddevice.CoreAudioSettings.__init__
        ).parameters
        for name in coreaudio.DIRECT_FLAGS:
            assert name in taken

    def test_the_real_settings_carry_the_portaudio_flags_those_names_mean(
        self,
    ) -> None:
        """The other half: the names are right and they mean what is wanted.

        Read off the built library rather than a manual. It is also how
        `paMacCorePro` was found to be nothing more than the first of them,
        which is why nothing here claims the device was taken.
        """
        flags = coreaudio.sounddevice._lib
        assert flags.paMacCoreChangeDeviceParameters
        assert flags.paMacCoreFailIfConversionRequired
        assert flags.paMacCorePro == flags.paMacCoreChangeDeviceParameters

    def test_the_track_s_own_rate_is_what_is_asked_for(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        seen = asked(monkeypatch)
        coreaudio.open_output(request(OutputMode.EXCLUSIVE))
        assert seen["attempts"][0]["samplerate"] == RATE

    def test_nothing_is_probed_before_the_stream_is_opened(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A probe with those flags can disturb another program's playback."""

        def refuse_to_be_asked(**_kwargs):
            raise AssertionError("a probe would interrupt somebody else's music")

        monkeypatch.setattr(
            coreaudio.sounddevice, "check_output_settings", refuse_to_be_asked
        )
        asked(monkeypatch)
        coreaudio.open_output(request(OutputMode.EXCLUSIVE))

    def test_what_opened_is_reported_as_the_mode_that_was_asked_for(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        asked(monkeypatch)
        _stream, report, _dtype = coreaudio.open_output(request(OutputMode.EXCLUSIVE))
        assert report.mode is OutputMode.EXCLUSIVE
        assert report.rate_is_native
        assert report.is_bit_perfect


class TestWhenItCannotHaveIt:
    def test_a_refused_stream_falls_back_to_the_mixer_with_the_reason(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        seen = asked(monkeypatch, refuse=True)
        _stream, report, dtype = coreaudio.open_output(request(OutputMode.EXCLUSIVE))
        assert report.mode is OutputMode.SHARED
        assert report.fell_back
        assert "will not run at that rate" in report.fallback_reason
        assert dtype == coreaudio.SHARED_DTYPE
        assert len(seen["attempts"]) == 2, "the direct attempt, then the mixer"

    def test_a_file_stating_no_depth_is_refused_before_the_device_is_asked(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A lossy source has no depth to deliver untouched, whatever opens."""
        seen = asked(monkeypatch)
        _stream, report, _dtype = coreaudio.open_output(
            request(OutputMode.EXCLUSIVE, depth=NO_DEPTH)
        )
        assert report.mode is OutputMode.SHARED
        assert report.fallback_reason == coreaudio.NO_STATED_DEPTH
        assert len(seen["attempts"]) == 1, "only the mixer was ever asked"

    def test_asking_for_the_mixer_asks_for_nothing_else(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        seen = asked(monkeypatch)
        _stream, report, _dtype = coreaudio.open_output(request(OutputMode.SHARED))
        assert report.mode is OutputMode.SHARED
        assert report.fallback_reason == "", "the mixer was what was wanted"
        assert "extra_settings" not in seen["attempts"][0]

    def test_a_portaudio_without_core_audio_support_says_so_and_carries_on(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Measured on Windows: the symbol the settings need is not there.

        A Mac user running such a build is owed the mixer and a reason rather
        than a stack trace, so the settings failing is a fallback like any
        other refusal.
        """
        seen = asked(monkeypatch)

        def missing_symbol():
            raise OSError("symbol 'PaMacCore_SetupStreamInfo' not found")

        monkeypatch.setattr(coreaudio, "direct_settings", missing_symbol)
        _stream, report, _dtype = coreaudio.open_output(request(OutputMode.EXCLUSIVE))
        assert report.mode is OutputMode.SHARED
        assert "PaMacCore_SetupStreamInfo" in report.fallback_reason
        assert len(seen["attempts"]) == 1, "only the mixer ever opened"

    def test_no_output_at_all_is_raised_rather_than_reported(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A machine with no usable device is a failure, not a fallback."""

        def no_device(**_kwargs):
            raise RuntimeError("no device")

        monkeypatch.setattr(coreaudio.sounddevice, "OutputStream", no_device)
        monkeypatch.setattr(coreaudio, "default_device", lambda: None)
        with pytest.raises(coreaudio.OutputUnavailableError):
            coreaudio.open_output(request(OutputMode.SHARED))
