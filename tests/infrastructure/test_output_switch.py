"""Which output module a platform plays through.

The switch is the whole of what the application knows about there being more
than one. It is asserted rather than trusted because it cannot be exercised
both ways on one machine: the Windows branch is the only one that runs here, so
the other branch would otherwise ship on a reading of the source alone.

`sys.platform` is stood in for, which is what lets a Windows machine ask what a
Mac would have done.
"""

from __future__ import annotations

import pytest

from stellody.infrastructure import output

ANSWER = ("stream", "report", "dtype")
MACOS = "darwin"
LINUX = "linux"


def routed(monkeypatch: pytest.MonkeyPatch, platform: str) -> list[str]:
    """Record which module the switch reached, under a stated platform."""
    reached: list[str] = []

    def portable(*_args, **_kwargs):
        reached.append("portaudio")
        return ANSWER

    def windows(*_args, **_kwargs):
        reached.append("wasapi")
        return ANSWER

    def mac(*_args, **_kwargs):
        reached.append("coreaudio")
        return ANSWER

    from stellody.infrastructure import coreaudio, wasapi

    monkeypatch.setattr(output.sys, "platform", platform)
    monkeypatch.setattr(output.portaudio, "open_output", portable)
    monkeypatch.setattr(wasapi, "open_output", windows)
    monkeypatch.setattr(coreaudio, "open_output", mac)
    return reached


@pytest.mark.parametrize("platform", [LINUX, "freebsd13", "sunos5"])
def test_everything_unnamed_takes_the_substrate(
    monkeypatch: pytest.MonkeyPatch, platform: str
) -> None:
    """The safe direction to fail in.

    A platform nobody has thought about plays through its mixer rather than
    not at all, so the one named here is an example rather than the rule.
    Linux is in the list DELIBERATELY: it was ruled out with Oliver on
    2026-09-17 rather than merely not reached yet.
    """
    reached = routed(monkeypatch, platform)
    assert output.open_output("request") == ANSWER
    assert reached == ["portaudio"]


def test_a_mac_takes_the_core_audio_module(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Running the device at the track's own rate is why that branch exists."""
    reached = routed(monkeypatch, MACOS)
    assert output.open_output("request") == ANSWER
    assert reached == ["coreaudio"]


@pytest.mark.parametrize(
    ("platform", "offered"),
    [
        (output.WINDOWS, True),
        (MACOS, True),
        (LINUX, False),
        ("freebsd13", False),
    ],
)
def test_which_platforms_have_a_route_past_the_mixer(
    platform: str, offered: bool
) -> None:
    """What the window stands the control down on; Linux is a decision."""
    assert output.offers_exclusive(platform) is offered


def test_the_platform_is_read_from_the_system_when_none_is_named(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The window asks without arguments, so the default cannot be untested."""
    monkeypatch.setattr(output.sys, "platform", LINUX)
    assert output.offers_exclusive() is False
    monkeypatch.setattr(output.sys, "platform", output.WINDOWS)
    assert output.offers_exclusive() is True


def test_windows_takes_the_host_api_it_has(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Exclusive mode is the whole reason this branch exists."""
    reached = routed(monkeypatch, output.WINDOWS)
    assert output.open_output("request") == ANSWER
    assert reached == ["wasapi"]


def test_what_the_caller_asked_reaches_the_module_unchanged(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The switch chooses; it does not interpret."""
    seen: dict = {}

    def portable(*args, **kwargs):
        seen["args"] = args
        seen["kwargs"] = kwargs
        return ANSWER

    monkeypatch.setattr(output.sys, "platform", LINUX)
    monkeypatch.setattr(output.portaudio, "open_output", portable)
    output.open_output("request", device=3)
    assert seen["args"] == ("request",)
    assert seen["kwargs"] == {"device": 3}
