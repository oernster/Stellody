"""A name several artists share, settled by what the library holds. FR-D09.

Reported by Oliver on 2026-09-27: Anyma was never shown as an artist held,
because MusicBrainz knows a second, unrelated Anyma. Measured the same day, 36
of a library's source artists went unasked that way.
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
from stellody.application.settling import MOST_EVIDENCE
from stellody.domain.credit_evidence import EvidenceKind

MEANT = "anyma-milleri"
NAMESAKE = "anyma-kubis"
BOTH = {"Anyma": (MEANT, NAMESAKE)}


def _run(catalogue: Catalogue, *albums) -> tuple:
    """The report of a run over these albums, with the catalogue to read."""
    run = Discovery(catalogue=catalogue, similarity=Similarity(), pause=Waits())
    return run.run(albums, ROCK, nothing, never), catalogue


def test_a_held_album_credited_to_one_namesake_settles_it() -> None:
    catalogue = Catalogue(identities=BOTH, credits={"Genesys": (MEANT,)})
    report, asked = _run(catalogue, make_album("Anyma", "Genesys (Deluxe)"))
    assert report.ambiguous == ()
    assert [gaps.artist for gaps in report.gaps] == ["Anyma"]
    assert asked.albums_asked == [MEANT]
    assert asked.credits_asked[0].kind is EvidenceKind.ALBUM


def test_a_track_settles_an_artist_met_only_on_a_compilation() -> None:
    catalogue = Catalogue(
        identities={"Bonobo": ("bonobo-green", "bonobo-nl")},
        credits={"Track 1": ("bonobo-green", "somebody-else")},
    )
    run = Discovery(catalogue=catalogue, similarity=Similarity(), pause=Waits())
    report = run.run(
        (make_compilation("Rock", "Bonobo"),), ROCK, nothing, never, compilations=True
    )
    assert report.ambiguous == ()
    assert catalogue.albums_asked == ["bonobo-green"]


def test_two_namesakes_credited_on_one_title_stay_ambiguous() -> None:
    """Measured for The Wash, Leonardo and Matador: a real ambiguity."""
    catalogue = Catalogue(identities=BOTH, credits={"Genesys": (MEANT, NAMESAKE)})
    report, asked = _run(catalogue, make_album("Anyma", "Genesys"))
    assert report.ambiguous[0].identifiers == (MEANT, NAMESAKE)
    assert asked.albums_asked == []


def test_a_title_crediting_nobody_gives_way_to_the_next() -> None:
    catalogue = Catalogue(identities=BOTH, credits={"A Track": (MEANT,)})
    report, asked = _run(catalogue, make_album("Anyma", "Genesys"))
    assert report.ambiguous == ()
    assert [piece.title for piece in asked.credits_asked] == ["Genesys", "A Track"]


def test_no_more_than_the_cap_is_tried() -> None:
    albums = tuple(make_album("Anyma", f"Album {n}") for n in range(MOST_EVIDENCE + 2))
    report, asked = _run(Catalogue(identities=BOTH), *albums)
    assert report.ambiguous[0].artist == "Anyma"
    assert len(asked.credits_asked) == MOST_EVIDENCE


def test_one_name_reaching_one_artist_asks_nothing_more() -> None:
    catalogue = Catalogue(identities={"Anyma": (MEANT,)})
    _, asked = _run(catalogue, make_album("Anyma", "Genesys"))
    assert asked.credits_asked == []
