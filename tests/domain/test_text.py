"""Text normalisation, ordering and file-name parsing."""

from __future__ import annotations

import pytest

from stellody.domain import text


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("  Royal   Blood ", "Royal Blood"),
        ("Rag’n’Bone Man", "Rag'n'Bone Man"),
        ("Peter Green‘s", "Peter Green's"),
        ("Skʼy", "Sk'y"),
        ("“Quoted”", '"Quoted"'),
        ("plain", "plain"),
    ],
)
def test_normalise_collapses_variants(raw: str, expected: str) -> None:
    assert text.normalise(raw) == expected


def test_comparison_key_ignores_case_but_not_articles() -> None:
    assert text.comparison_key("The Police") == text.comparison_key("the police")
    assert text.comparison_key("The Police") != text.comparison_key("Police")


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("The Police", "police"),
        ("A Perfect Circle", "perfect circle"),
        ("An Endless Sporadic", "endless sporadic"),
        ("deadmau5", "deadmau5"),
        ("twenty one pilots", "twenty one pilots"),
        ("Theatre of Tragedy", "theatre of tragedy"),
    ],
)
def test_sort_key_strips_only_a_leading_article(name: str, expected: str) -> None:
    assert text.sort_key(name) == expected


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Sasha; John Digweed", ("Sasha", "John Digweed")),
        ("Chicane feat. Bryan Adams", ("Chicane", "Bryan Adams")),
        ("A ft. B", ("A", "B")),
        ("A vs B", ("A", "B")),
        ("Lane 8/Kidnap", ("Lane 8", "Kidnap")),
        ("Solo Artist", ("Solo Artist",)),
        ("", ()),
        ("  ;  ", ()),
    ],
)
def test_split_artists(raw: str, expected: tuple[str, ...]) -> None:
    assert text.split_artists(raw) == expected


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("01. Mars.flac", (None, 1)),
        ("07 - Venus.flac", (None, 7)),
        ("1-01 Mars.flac", (1, 1)),
        ("2_05 Jupiter.flac", (2, 5)),
        ("110. Long.flac", (None, 110)),
        ("Mars.flac", (None, None)),
        ("", (None, None)),
    ],
)
def test_filename_ordinal(name: str, expected: tuple[int | None, int | None]) -> None:
    assert text.filename_ordinal(name) == expected


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("01. Mars, the Bringer of War.flac", "Mars, the Bringer of War"),
        ("07 - Venus.flac", "Venus"),
        ("1-01 Mars.flac", "Mars"),
        ("Untitled.flac", "Untitled"),
        ("noextension", "noextension"),
        ("03. .flac", "03."),
    ],
)
def test_filename_title(name: str, expected: str) -> None:
    assert text.filename_title(name) == expected


@pytest.mark.parametrize(
    ("date", "expected"),
    [("1997", 1997), ("2020-03-27", 2020), ("released 1989", 1989), ("", None)],
)
def test_year_of(date: str, expected: int | None) -> None:
    assert text.year_of(date) == expected


@pytest.mark.parametrize(
    ("artist", "expected"),
    [
        ("Various Artists", True),
        ("various artists", True),
        ("Various", True),
        ("VA", True),
        ("Verschiedene", True),
        ("Sasha", False),
    ],
)
def test_is_various_artists(artist: str, expected: bool) -> None:
    assert text.is_various_artists(artist) is expected
