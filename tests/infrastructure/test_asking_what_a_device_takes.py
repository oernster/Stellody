"""Asking a device which rates it will take exclusively, without opening one.

Added on 2026-09-18 after Oliver made the point that a control offering a mode
the machine cannot deliver is misleading. Answering that needs the question
asked before the music starts rather than after a refusal, so it has to be
cheap and silent: `check_output_settings` asks the driver whether a format
would be accepted and opens nothing.

Measured on his machine the same day, which is why the answer matters: the
onboard Realtek speakers take 44100, 48000, 96000 and 192000, while the
Bluetooth headphone that was his default takes 48000 alone. A 44.1 kHz album
was therefore refused every time, with a reason that named no way forward.
"""

from __future__ import annotations

import pytest

from stellody.infrastructure import output, portaudio, wasapi

LINUX = "linux"
MACOS = "darwin"


def answering(monkeypatch: pytest.MonkeyPatch, taken: set[int]) -> list[int]:
    """Let a stated set of rates through the probe; record everything asked."""
    asked: list[int] = []

    def check(**kwargs):
        asked.append(kwargs["samplerate"])
        if kwargs["samplerate"] not in taken:
            raise RuntimeError("the device will not take that")

    monkeypatch.setattr(wasapi.sounddevice, "check_output_settings", check)
    monkeypatch.setattr(wasapi, "default_device", lambda: None)
    return asked


class TestWhatTheDriverSays:
    def test_only_the_rates_it_accepts_come_back(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        answering(monkeypatch, {48000, 96000})
        assert wasapi.exclusive_rates() == (48000, 96000)

    def test_a_device_that_accepts_nothing_answers_nothing(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Empty is a real answer: it is what stands the switch down."""
        answering(monkeypatch, set())
        assert wasapi.exclusive_rates() == ()

    def test_every_rate_real_music_arrives_at_is_asked_about(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """An empty answer must mean the device, never a list that was too short."""
        asked = answering(monkeypatch, set())
        wasapi.exclusive_rates()
        assert set(asked) >= {44100, 48000, 88200, 96000, 176400, 192000}

    def test_it_asks_exclusively_or_the_answer_would_be_meaningless(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The mixer takes every rate, so a shared probe answers yes to all."""
        seen: list[object] = []

        def check(**kwargs):
            seen.append(kwargs["extra_settings"])

        monkeypatch.setattr(wasapi.sounddevice, "check_output_settings", check)
        monkeypatch.setattr(wasapi, "default_device", lambda: None)
        wasapi.exclusive_rates()
        assert seen, "nothing was asked at all"
        assert all(settings is not None for settings in seen)

    def test_the_device_it_was_given_is_the_device_it_asks_about(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A listener who moved their output is owed the new device's answer."""
        seen: list[object] = []

        def check(**kwargs):
            seen.append(kwargs["device"])
            raise RuntimeError("no")

        monkeypatch.setattr(wasapi.sounddevice, "check_output_settings", check)
        monkeypatch.setattr(
            wasapi, "default_device", lambda: pytest.fail("it asked the wrong device")
        )
        wasapi.exclusive_rates(7)
        assert set(seen) == {7}

    def test_nothing_is_opened_and_nothing_is_played(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The whole point of a probe: it may not interrupt what is playing."""

        def refuse(**_kwargs):
            raise AssertionError("a probe must not open a stream")

        monkeypatch.setattr(wasapi.sounddevice, "OutputStream", refuse)
        answering(monkeypatch, {48000})
        assert wasapi.exclusive_rates() == (48000,)


class TestWhichPlatformAnswersWhat:
    def test_windows_asks_its_own_devices(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(output.sys, "platform", output.WINDOWS)
        monkeypatch.setattr(wasapi, "exclusive_rates", lambda device: (48000,))
        assert output.exclusive_rates() == (48000,)

    def test_a_mac_is_not_asked_at_all(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """The flags that would answer may disturb another program's playback.

        None rather than an empty tuple: an unanswered question is not a no,
        so nothing is stood down on it.
        """
        monkeypatch.setattr(output.sys, "platform", MACOS)
        assert output.exclusive_rates() is None

    def test_linux_answers_none_at_all_rather_than_unknown(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """It is a decision there rather than an open question; see output.py."""
        monkeypatch.setattr(output.sys, "platform", LINUX)
        assert output.exclusive_rates() == ()

    def test_the_substrate_still_refuses_exclusive_mode_itself(self) -> None:
        """Guard the guard: the rates answer must agree with the opener."""
        assert portaudio.NO_EXCLUSIVE_HERE
        assert not output.offers_exclusive(LINUX)
