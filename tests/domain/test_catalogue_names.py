"""Reading a catalogue's names the way a tag typed them. FR-D08, FR-D53.

Every case here is a name a real run failed on, measured on 2026-09-27: the
catalogue held the artist and the tag spelled it with what a keyboard types.
"""

from __future__ import annotations

import pytest

from stellody.domain.text import (
    bare_title,
    catalogue_key,
    catalogue_name,
    comparison_key,
    credit_parts,
)

# The hyphen MusicBrainz writes in Jerome Isma-Ae, which no keyboard types.
CATALOGUE_HYPHEN = chr(0x2010)
MINUS_SIGN = chr(0x2212)


@pytest.mark.parametrize(
    ("typed", "catalogued"),
    [
        ("Hernan Cattaneo", "Hernán Cattáneo"),
        ("Andre Sobota", "André Sobota"),
        ("Jerome Isma-Ae", f"Jerome Isma{CATALOGUE_HYPHEN}Ae"),
        ("A-B", f"A{MINUS_SIGN}B"),
        ("JOBE (10)", "JOBE"),
        ("anyma", "Anyma"),
    ],
)
def test_a_typed_name_matches_what_the_catalogue_writes(
    typed: str, catalogued: str
) -> None:
    assert catalogue_key(typed) == catalogue_key(catalogued)


def test_different_names_stay_different() -> None:
    assert catalogue_key("Anyma") != catalogue_key("Anyma (UK)")


def test_the_library_key_stays_strict() -> None:
    """Two spellings in the library are the listener's own filing to keep."""
    assert comparison_key("Hernan Cattaneo") != comparison_key("Hernán Cattáneo")


def test_a_discogs_number_is_not_asked_for() -> None:
    assert catalogue_name("Spencer Brown (4)") == "Spencer Brown"


def test_a_bracketed_word_is_kept_in_the_name() -> None:
    """Only Discogs' numbers go; "(UK)" may be part of a name the catalogue holds."""
    assert catalogue_name("Anyma (UK)") == "Anyma (UK)"


def test_a_name_that_is_only_a_number_stays_whole() -> None:
    assert catalogue_name("(10)") == "(10)"


@pytest.mark.parametrize(
    ("title", "bare"),
    [
        ("Galaxy (Mixed) Mixed", "Galaxy"),
        ("Stars [Mano Le Tough Remix]", "Stars"),
        ("Genesys", "Genesys"),
        ("(Intro)", "(Intro)"),
    ],
)
def test_a_title_is_searched_up_to_its_first_bracket(title: str, bare: str) -> None:
    assert bare_title(title) == bare


@pytest.mark.parametrize(
    ("credit", "parts"),
    [
        ("Rone Featuring Noga Erez", ("Rone", "Noga Erez")),
        ("andhim feat. Högni", ("andhim", "Högni")),
        ("Kapote Feat Mona Lazette", ("Kapote", "Mona Lazette")),
        ("KI Creighton ft. Jem Cooke", ("KI Creighton", "Jem Cooke")),
    ],
)
def test_a_featured_guest_comes_apart(credit: str, parts: tuple[str, ...]) -> None:
    assert credit_parts(credit) == parts


def test_featuring_inside_a_word_is_not_a_join() -> None:
    assert credit_parts("Defeat Featurette") == ()
