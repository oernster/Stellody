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

    from stellody.infrastructure import wasapi

    monkeypatch.setattr(output.sys, "platform", platform)
    monkeypatch.setattr(output.portaudio, "open_output", portable)
    monkeypatch.setattr(wasapi, "open_output", windows)
    return reached


@pytest.mark.parametrize("platform", [MACOS, LINUX, "freebsd13", "sunos5"])
def test_everything_that_is_not_windows_takes_the_substrate(
    monkeypatch: pytest.MonkeyPatch, platform: str
) -> None:
    """The safe direction to fail in.

    A platform nobody has thought about plays through its mixer rather than
    not at all, so the two named here are examples rather than the rule.
    """
    reached = routed(monkeypatch, platform)
    assert output.open_output("request") == ANSWER
    assert reached == ["portaudio"]


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
