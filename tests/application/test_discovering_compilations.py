"""FR-D53: a compilation credit nobody is found under is asked about by its parts.

Driven against the same hand-written catalogues as every other run test, so
what is asserted is which questions are asked and in what order.
"""

from __future__ import annotations

from discovery_support import (
    ROCK,
    Catalogue,
    Similarity,
    Waits,
    make_album,
    make_compilation,
    never,
    nothing,
)

from stellody.application.discovering import Discovery
from stellody.application.values import RunOutcome, RunReport
from stellody.domain.album import Album

# What the catalogue answers for a name it reaches nobody under.
UNKNOWN: tuple[str, ...] = ()


def run_over(
    albums: tuple[Album, ...], catalogue: Catalogue, compilations: bool = True
) -> RunReport:
    """One run over these albums, compilations included unless said otherwise."""
    service = Discovery(catalogue=catalogue, similarity=Similarity(), pause=Waits())
    return service.run(albums, ROCK, nothing, never, compilations=compilations)


def test_an_unrecognised_credit_is_asked_about_by_its_parts() -> None:
    """ODESZA & Bettye LaVette reaches nobody whole; each half is somebody."""
    credit = "ODESZA & Bettye LaVette"
    catalogue = Catalogue(identities={credit: UNKNOWN})
    report = run_over((make_compilation("Rock", credit),), catalogue)
    assert catalogue.identified == [credit, "ODESZA", "Bettye LaVette"]
    assert credit not in report.unresolved


def test_a_recognised_credit_is_not_split() -> None:
    """Eli & Fur is one duo, so knowing the whole name ends the question."""
    catalogue = Catalogue()
    run_over((make_compilation("Rock", "Eli & Fur"),), catalogue)
    assert catalogue.identified == ["Eli & Fur"]


def test_a_part_nobody_knows_is_reported_unrecognised() -> None:
    """The fallback is honest about a half it could not find either."""
    catalogue = Catalogue(identities={"Dilby & Nobody": UNKNOWN, "Nobody": UNKNOWN})
    report = run_over((make_compilation("Rock", "Dilby & Nobody"),), catalogue)
    assert report.unresolved == ("Nobody",)


def test_a_part_already_asked_about_is_not_asked_again() -> None:
    """One artist is one question, however they reached the run."""
    catalogue = Catalogue(identities={"Dilby & Tinlicker": UNKNOWN})
    run_over((make_compilation("Rock", "Dilby", "Dilby & Tinlicker"),), catalogue)
    assert catalogue.identified == ["Dilby", "Dilby & Tinlicker", "Tinlicker"]


def test_an_album_artist_nobody_knows_is_not_split() -> None:
    """The name an album is filed under is the listener's, so it stays whole."""
    catalogue = Catalogue(identities={"Simon & Garfunkel": UNKNOWN})
    report = run_over((make_album("Simon & Garfunkel", "Bookends"),), catalogue)
    assert catalogue.identified == ["Simon & Garfunkel"]
    assert report.unresolved == ("Simon & Garfunkel",)


def test_a_run_leaving_compilations_out_asks_nothing_of_them() -> None:
    """Left out is the default; it asks nobody about a compilation."""
    catalogue = Catalogue()
    held = (make_compilation("Rock", "Dilby"),)
    report = run_over(held, catalogue, compilations=False)
    assert report.outcome is RunOutcome.NOTHING_TO_ASK
    assert catalogue.identified == []
