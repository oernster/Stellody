"""When the system's own mixer leaves nothing to hear. `OUTPUTS.md` FR-O21."""

from __future__ import annotations

import pytest

from stellody.domain.playback import SILENT_VOLUME, UNITY_VOLUME, SystemVolume

# A level well below unity, as Windows held Stellody at after it was put
# right by hand on 2026-10-25: quiet is not silent.
QUIET = 0.1


@pytest.mark.parametrize(
    ("level", "muted", "silences"),
    [
        (UNITY_VOLUME, False, False),
        (QUIET, False, False),
        (SILENT_VOLUME, False, True),
        (UNITY_VOLUME, True, True),
        (SILENT_VOLUME, True, True),
    ],
)
def test_only_nought_or_a_mute_silences(
    level: float, muted: bool, silences: bool
) -> None:
    """Nought or muted leaves nothing; any level above nought is heard."""
    assert SystemVolume(level=level, muted=muted).silences is silences
