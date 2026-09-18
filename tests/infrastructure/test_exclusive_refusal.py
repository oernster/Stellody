"""FR-F06: an exclusive stream is refused for a file that states no depth.

The refusal names the file rather than the device, since the device could well
have opened. Nothing here opens one: the mixer path the refusal falls back to is
stood in front of, so what is read is the reason it was handed.
"""

from __future__ import annotations

import pytest

from stellody.domain.formats import LOSSY_FAMILIES, stored_depth
from stellody.domain.playback import OutputMode, OutputRequest
from stellody.domain.track import CD_BIT_DEPTH, CD_SAMPLE_RATE
from stellody.infrastructure import portaudio, wasapi

# Any device number: the refusal comes before a device is consulted.
A_DEVICE = 0


@pytest.mark.parametrize("family", sorted(LOSSY_FAMILIES))
def test_a_lossy_source_is_refused_exclusive_for_the_file(
    family: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The reason says the file stated no depth; the device is not blamed."""
    handed: list[str] = []

    def mixer(_open, _device, _request, reason: str) -> None:
        handed.append(reason)

    monkeypatch.setattr(wasapi, "opened_shared", mixer)
    request = OutputRequest(
        sample_rate=CD_SAMPLE_RATE,
        bit_depth=stored_depth(family, CD_BIT_DEPTH),
        mode=OutputMode.EXCLUSIVE,
    )
    wasapi.open_output(request, device=A_DEVICE)
    assert handed == [portaudio.NO_STATED_DEPTH]
    assert "file" in portaudio.NO_STATED_DEPTH, "the file is named, not the device"
