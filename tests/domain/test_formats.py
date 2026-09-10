"""Which stated depths are believed, tested with no file anywhere near it.

FR-F06 and FR-F07 are one rule read in two directions, so they are tested as
one rule: a lossy family reports nought whatever it stated and every other
family keeps what it stated. Both cases are pure arithmetic over a number, so
neither needs a fixture, a decoder or a disk.
"""

from __future__ import annotations

import pytest

from stellody.domain.formats import (
    FAMILY_AAC,
    FAMILY_MP4_LOSSY,
    FAMILY_OTHER,
    FAMILY_WMA,
    LOSSY_FAMILIES,
    stored_depth,
    stores_its_samples,
)
from stellody.domain.track import CD_BIT_DEPTH

STUDIO_DEPTH = 24


@pytest.mark.parametrize("family", sorted(LOSSY_FAMILIES))
def test_a_lossy_family_stores_no_depth_whatever_it_stated(family: str) -> None:
    """FR-F06. The container's field is not evidence of a stored sample."""
    assert stores_its_samples(family) is False
    assert stored_depth(family, CD_BIT_DEPTH) == 0
    assert stored_depth(family, STUDIO_DEPTH) == 0
    assert stored_depth(family, 0) == 0


def test_the_three_lossy_families_are_the_ones_named() -> None:
    """The membership itself, so widening it is a decision rather than a drift."""
    assert LOSSY_FAMILIES == frozenset({FAMILY_MP4_LOSSY, FAMILY_WMA, FAMILY_AAC})


@pytest.mark.parametrize("stated", [CD_BIT_DEPTH, STUDIO_DEPTH, 32])
def test_any_other_family_keeps_the_depth_it_stated(stated: int) -> None:
    """FR-F07. WavPack is the case this exists for; it arrives as any other."""
    assert stores_its_samples(FAMILY_OTHER) is True
    assert stored_depth(FAMILY_OTHER, stated) == stated


def test_a_family_nobody_named_keeps_its_depth() -> None:
    """The direction of the rule, which is the half worth pinning.

    A format added later and forgotten here reports what it states rather than
    losing a bit-perfect stream it had earned. The opposite default would fail
    silently, which is the failure this test exists to prevent.
    """
    assert stored_depth("a format nobody has written yet", CD_BIT_DEPTH) == CD_BIT_DEPTH


@pytest.mark.parametrize("nonsense", [0, -1, -16])
def test_a_depth_no_format_states_reports_none(nonsense: int) -> None:
    """Nought is absent and a negative figure is nonsense; both read as absent."""
    assert stored_depth(FAMILY_OTHER, nonsense) == 0
