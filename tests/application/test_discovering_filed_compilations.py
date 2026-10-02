"""FR-D82: a compilation filed under the DJ who mixed it brings its series.

Driven through a whole run, as `test_discovering_series.py` beside this is,
whose fakes it shares.
"""

from __future__ import annotations

from discovery_support import Catalogue, make_album
from test_discovering_series import GU, SeriesCatalogue, run_over, the_series

from stellody.application.discovery_ports import SourceFailed
from stellody.application.values import RunOutcome
from stellody.domain.discovery import ReleaseGroup
from stellody.domain.matching import ReleaseKind
from stellody.domain.series import Series

TENAGLIA_HELD = "Global Underground #45: Danny Tenaglia - Brooklyn"
TENAGLIA_CATALOGUED = "Global Underground 045: Danny Tenaglia in Brooklyn"
WARREN = "Global Underground 046: Nick Warren in Shanghai"


def numbered_series() -> SeriesCatalogue:
    """The numbered Global Underground series, placed by the catalogue's title."""
    entries = (ReleaseGroup(title=TENAGLIA_CATALOGUED), ReleaseGroup(title=WARREN))
    return SeriesCatalogue(
        places={TENAGLIA_CATALOGUED: ("gu",)},
        series={"gu": Series(GU, entries)},
    )


def tenaglia(*identities: str) -> Catalogue:
    """Danny Tenaglia under these identities, the mix typed as one."""
    mix = ReleaseGroup(
        title=TENAGLIA_CATALOGUED,
        kinds=(ReleaseKind.COMPILATION, ReleaseKind.DJ_MIX),
    )
    return Catalogue(
        identities={"Danny Tenaglia": identities},
        albums={identity: (mix,) for identity in identities},
    )


HELD = (make_album("Danny Tenaglia", TENAGLIA_HELD, "House"),)


def test_a_compilation_filed_under_its_dj_brings_its_series() -> None:
    """Searched by the catalogue's title, since "#45" never finds "045"."""
    series = numbered_series()
    report = run_over(HELD, series, tenaglia("dt"))
    assert ("series_of", TENAGLIA_CATALOGUED) in series.asked
    assert the_series(report) == {GU: (WARREN,)}


def test_a_dj_the_library_cannot_settle_brings_no_series() -> None:
    """Two namesakes and no title to tell them apart: nothing is searched."""
    series = numbered_series()
    run_over(HELD, series, tenaglia("dt", "another"))
    assert series.asked == []


def test_a_dj_nobody_could_look_up_brings_no_series() -> None:
    """The artist stage has already reported the failure; this adds nothing."""
    series = numbered_series()
    report = run_over(HELD, series, Catalogue(raises=SourceFailed("broken")))
    assert report.outcome is RunOutcome.COMPLETED
    assert series.asked == []


def test_left_out_compilations_bring_no_series() -> None:
    """The box decides, as it does for every series. FR-D51."""
    series = numbered_series()
    run_over(HELD, series, tenaglia("dt"), compilations=False)
    assert series.asked == []
