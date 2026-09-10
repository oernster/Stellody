"""What an output request built from a widened lossy source may claim.

`test_playback.py` holds the request and report rules in general. This file
holds one of them read against the formats `FORMATS.md` adds, because that is
the promise most at risk when a lossy format joins a library: a track badged as
delivered untouched when a decoder has already changed it.

Nothing here opens a device. The claim is refused by the request itself, which
is the point: a rule held in the domain cannot be lost by a device saying yes.
"""

from __future__ import annotations

import pytest

from stellody.domain.formats import LOSSY_FAMILIES, stored_depth
from stellody.domain.playback import OutputMode, OutputReport, OutputRequest
from stellody.domain.track import CD_BIT_DEPTH, CD_SAMPLE_RATE

# What a device would report having opened, which is deliberately generous:
# the point is that a stream opening at CD depth in exclusive mode still
# cannot make the claim when the file behind it stated no depth.
DEVICE_DEPTH = CD_BIT_DEPTH


@pytest.mark.parametrize("family", sorted(LOSSY_FAMILIES))
def test_a_widened_lossy_source_is_never_bit_perfect(family: str) -> None:
    """FR-F06, read the whole way to the claim it exists to refuse."""
    depth = stored_depth(family, CD_BIT_DEPTH)
    request = OutputRequest(
        sample_rate=CD_SAMPLE_RATE, bit_depth=depth, mode=OutputMode.EXCLUSIVE
    )

    assert request.states_depth is False

    report = OutputReport(
        request=request,
        mode=OutputMode.EXCLUSIVE,
        sample_rate=CD_SAMPLE_RATE,
        bit_depth=DEVICE_DEPTH,
    )

    assert report.rate_is_native is True
    assert report.depth_is_native is False
    assert report.is_bit_perfect is False


def test_a_widened_lossless_source_can_still_be_bit_perfect() -> None:
    """The other direction, so the refusal above is a rule rather than a floor.

    WavPack is why this is here: it is lossless, it states a real depth and it
    arrives through the same widening. A guard written only against the lossy
    formats would have taken this claim away from it.
    """
    request = OutputRequest(
        sample_rate=CD_SAMPLE_RATE,
        bit_depth=stored_depth("wavpack", CD_BIT_DEPTH),
        mode=OutputMode.EXCLUSIVE,
    )

    assert request.states_depth is True

    report = OutputReport(
        request=request,
        mode=OutputMode.EXCLUSIVE,
        sample_rate=CD_SAMPLE_RATE,
        bit_depth=DEVICE_DEPTH,
    )

    assert report.is_bit_perfect is True
