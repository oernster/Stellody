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


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        # Every shape measured across the reference library, with the count of
        # files carrying it, so a change to this rule is read against what the
        # files actually hold rather than against what they might hold.
        ("2011-05-02", "2011-05-02"),  # 3,005 files
        ("2001", "2001"),  # 1,843 files
        ("2007-10-09T12:00:00Z", "2007-10-09"),  # 1,354 files
        ("1989-04", "1989-04"),  # 63 files
        ("2001 05 15", "2001-05-15"),  # 13 files
        # The other three placeholder times the store writes.
        ("1990-05-01T07:00:00Z", "1990-05-01"),
        ("1990-05-01T08:00:00Z", "1990-05-01"),
        ("1990-05-01T00:00:00Z", "1990-05-01"),
        # A real offset is dropped exactly as the fake one is, in both spellings.
        ("1990-05-01T12:00:00+01:00", "1990-05-01"),
        ("1990-05-01T12:00:00-0500", "1990-05-01"),
        # A time written with a space rather than the T that separates it.
        ("1990-05-01 12:00:00", "1990-05-01"),
        # Nothing is invented: a year stays a year and gains no month.
        ("1990", "1990"),
        ("", ""),
        # Whitespace is collapsed even where the shape is not recognised, since
        # that much is safe; the rest of an unfamiliar tag is left alone.
        ("  released   1989 ", "released 1989"),
        ("Spring 1990", "Spring 1990"),
        ("90-05-01", "90-05-01"),
        ("1990-5-1", "1990-5-1"),
    ],
)
def test_tag_date(raw: str, expected: str) -> None:
    assert text.tag_date(raw) == expected


def test_tag_date_keeps_the_year_the_rest_of_the_application_reads() -> None:
    """Reducing a date must not change which year an album is filed under."""
    for raw in ("2007-10-09T12:00:00Z", "2001 05 15", "1989-04", "2001"):
        assert text.year_of(text.tag_date(raw)) == text.year_of(raw)


def test_tag_date_is_idempotent() -> None:
    """Applying the rule twice must say what applying it once said.

    It is called where a tag is read and again where a cue sheet's date falls
    back on the file's, so a second pass over an already reduced value has to
    be a no-op rather than a second reduction.
    """
    for raw in ("2007-10-09T12:00:00Z", "2001 05 15", "1989-04", "Spring 1990"):
        once = text.tag_date(raw)
        assert text.tag_date(once) == once
