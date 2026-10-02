"""FR-D53: a name nobody is found under is asked about by its parts.

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
from stellody.domain.including import OWN_ALBUMS, WIDEST, Including

# What the catalogue answers for a name it reaches nobody under.
UNKNOWN: tuple[str, ...] = ()


def run_over(
    albums: tuple[Album, ...], catalogue: Catalogue, including: Including = WIDEST
) -> RunReport:
    """One run over these albums, everything taken in unless said otherwise."""
    service = Discovery(catalogue=catalogue, similarity=Similarity(), pause=Waits())
    return service.run(albums, ROCK, nothing, never, including=including)


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


def test_an_album_artist_nobody_knows_is_asked_about_by_its_parts() -> None:
    """Ruled by Oliver on 2026-09-27: "Seb Fontaine / John Kelly / Graeme Park"
    reached nobody whole and named three artists nobody was asking about."""
    whole = "Seb Fontaine / John Kelly / Graeme Park"
    catalogue = Catalogue(identities={whole: UNKNOWN})
    report = run_over((make_album(whole, "Perfecto Presents"),), catalogue)
    assert catalogue.identified == [whole, "Seb Fontaine", "John Kelly", "Graeme Park"]
    assert report.unresolved == ()


def test_an_album_artist_known_whole_is_not_split() -> None:
    """Asked whole first, so a duo named with an ampersand stays one duo."""
    catalogue = Catalogue()
    run_over((make_album("Simon & Garfunkel", "Bookends"),), catalogue)
    assert catalogue.identified == ["Simon & Garfunkel"]


def test_a_run_leaving_compilations_out_asks_nothing_of_them() -> None:
    """Left out is the default; it asks nobody about a compilation."""
    catalogue = Catalogue()
    held = (make_compilation("Rock", "Dilby"),)
    report = run_over(held, catalogue, including=OWN_ALBUMS)
    assert report.outcome is RunOutcome.NOTHING_TO_ASK
    assert catalogue.identified == []
