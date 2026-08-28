"""Reading values out of a raw tag mapping."""

from __future__ import annotations

import pytest

from stellody.application import tags


def test_values_takes_the_first_name_that_is_present() -> None:
    mapping = {"ALBUM ARTIST": ("Sasha",)}
    assert tags.values(mapping, tags.ALBUM_ARTIST) == ("Sasha",)


def test_values_skips_a_name_held_but_empty() -> None:
    mapping = {"ALBUMARTIST": (), "ALBUM ARTIST": ("Sasha",)}
    assert tags.values(mapping, tags.ALBUM_ARTIST) == ("Sasha",)


def test_values_discards_blank_entries() -> None:
    mapping = {"ARTIST": ("Sasha", "   ", "Digweed")}
    assert tags.values(mapping, tags.ARTIST) == ("Sasha", "Digweed")


def test_values_returns_nothing_when_no_name_matches() -> None:
    assert tags.values({}, tags.ALBUM) == ()


def test_first_normalises_and_falls_back_to_an_empty_string() -> None:
    assert tags.first({"ALBUM": ("  Involver ",)}, tags.ALBUM) == "Involver"
    assert tags.first({}, tags.ALBUM) == ""


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("7", 7),
        ("3/12", 3),
        ("07", 7),
        ("0", None),
        ("0/12", None),
        ("A", None),
        ("", None),
    ],
)
def test_number_tolerates_how_rippers_write_ordinals(
    raw: str, expected: int | None
) -> None:
    assert tags.number({"TRACKNUMBER": (raw,)}, tags.TRACK) == expected


def test_artists_keeps_repeated_fields_as_written() -> None:
    mapping = {"ARTIST": ("Chicane", "Bryan Adams")}
    assert tags.artists(mapping) == ("Chicane", "Bryan Adams")


def test_artists_splits_a_single_packed_field() -> None:
    mapping = {"ARTIST": ("Sasha feat. Kicks Like a Mule",)}
    assert tags.artists(mapping) == ("Sasha", "Kicks Like a Mule")


def test_artists_is_empty_when_nothing_is_credited() -> None:
    assert tags.artists({}) == ()
