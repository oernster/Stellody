"""Which output device a WASAPI stream is opened on.

Measured; it is why nothing played at all. Sounddevice's global default
output resolves through MME on the reference machine, so handing WASAPI
settings to an MME stream fails outright with "Incompatible host API specific
stream info", PaErrorCode -9984. Every route into playback died there, so this
module has to ask WASAPI which device it means rather than taking the default.

The host APIs are stood in for, because what is asserted is the choosing.
"""

from __future__ import annotations

import pytest

from stellody.infrastructure import wasapi

WASAPI_DEVICE = 30


def host_apis(**names: int) -> list[dict]:
    """A host API list in the shape sounddevice reports one."""
    return [
        {"name": name.replace("_", " "), "default_output_device": device}
        for name, device in names.items()
    ]


def test_the_wasapi_host_api_is_the_one_asked(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """MME comes first and is the global default; it is not the answer."""
    monkeypatch.setattr(
        wasapi.sounddevice,
        "query_hostapis",
        lambda: host_apis(
            MME=5,
            Windows_DirectSound=17,
            Windows_WASAPI=WASAPI_DEVICE,
            Windows_WDM_KS=49,
        ),
    )
    assert wasapi.default_device() == WASAPI_DEVICE


def test_a_machine_with_no_wasapi_at_all_chooses_nothing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Nothing to choose is not a fault; the caller falls back to the default."""
    monkeypatch.setattr(wasapi.sounddevice, "query_hostapis", lambda: host_apis(ALSA=1))
    assert wasapi.default_device() is None


def test_wasapi_present_but_holding_no_device_chooses_nothing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        wasapi.sounddevice,
        "query_hostapis",
        lambda: host_apis(Windows_WASAPI=wasapi.NO_DEVICE),
    )
    assert wasapi.default_device() is None


def test_a_machine_that_cannot_be_asked_chooses_nothing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """No sound hardware at all raises rather than answering."""

    def refuse():
        raise OSError("no host APIs")

    monkeypatch.setattr(wasapi.sounddevice, "query_hostapis", refuse)
    assert wasapi.default_device() is None
