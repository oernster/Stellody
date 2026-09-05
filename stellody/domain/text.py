"""Text normalisation and sort-key rules.

Album and artist names arrive from tags written by many different rippers, so
comparison and ordering both work on a normalised form rather than the raw
string. Nothing here touches the filesystem.
"""

from __future__ import annotations

import re
import unicodedata

VARIOUS_ARTISTS = "Various Artists"

_APOSTROPHES = str.maketrans(
    {
        "‘": "'",
        "’": "'",
        "ʼ": "'",
        "“": '"',
        "”": '"',
    }
)
_WHITESPACE = re.compile(r"\s+")
_LEADING_ARTICLE = re.compile(r"^(?:the|a|an)\s+", re.IGNORECASE)
_ARTIST_SEPARATORS = re.compile(r"\s*(?:;|/|\b(?:feat|ft|vs)\b\.?)\s*", re.IGNORECASE)
_FILENAME_ORDINAL = re.compile(
    r"^\s*(?:(?P<disc>\d{1,2})\s*[-_.]\s*)?(?P<track>\d{1,3})\s*[-_.\s]"
)
_YEAR = re.compile(r"(\d{4})")
# A date tag as the files of this library actually write one. Measured across
# 6,445 tagged files: a bare year, a year and month, a full date written with
# dashes or with spaces, and a full date wearing a time. The time is the reason
# this exists. Of the 1,354 files carrying one, every single value is UTC and
# only four times of day appear at all: noon, midnight, and the two forms of
# midnight in US Pacific. Those are the iTunes store's padding for a release
# DAY, so the hour names nothing that happened and the offset is not an offset.
# The trailing offset is admitted anyway, since a file written elsewhere may
# carry a real one and dropping it is the same act either way.
_TAG_DATE = re.compile(
    r"^(?P<year>\d{4})"
    r"(?:[- ](?P<month>\d{2})"
    r"(?:[- ](?P<day>\d{2})"
    r"(?:[T ]\d{2}:\d{2}:\d{2}(?:Z|[+-]\d{2}:?\d{2})?)?"
    r")?)?$"
)


def normalise(value: str) -> str:
    """Collapse unicode variants and whitespace without changing case."""
    folded = unicodedata.normalize("NFKC", value).translate(_APOSTROPHES)
    return _WHITESPACE.sub(" ", folded).strip()


def comparison_key(value: str) -> str:
    """A case-insensitive key for deciding whether two names are the same."""
    return normalise(value).casefold()


def sort_key(value: str) -> str:
    """An ordering key that ignores a leading article, so The Police sorts P."""
    return _LEADING_ARTICLE.sub("", normalise(value)).casefold()


def split_artists(value: str) -> tuple[str, ...]:
    """Split a single artist field that packs several names into one string."""
    parts = (normalise(part) for part in _ARTIST_SEPARATORS.split(value))
    return tuple(part for part in parts if part)


def filename_ordinal(file_name: str) -> tuple[int | None, int | None]:
    """Read a leading disc and track number from a file name.

    Understands the common shapes: "01. Title", "01 - Title" and "1-01 Title".
    Returns (disc, track); either element is None when the name does not say.
    """
    match = _FILENAME_ORDINAL.match(file_name)
    if match is None:
        return None, None
    disc = match.group("disc")
    return (int(disc) if disc is not None else None), int(match.group("track"))


def filename_title(file_name: str) -> str:
    """The part of a file name that follows its leading ordinal."""
    stem = file_name.rsplit(".", 1)[0] if "." in file_name else file_name
    match = _FILENAME_ORDINAL.match(stem)
    remainder = stem[match.end() :] if match is not None else stem
    cleaned = normalise(remainder.lstrip(" -_."))
    return cleaned or normalise(stem)


def year_of(date: str) -> int | None:
    """The four-digit year inside a date tag, which may be a full date."""
    match = _YEAR.search(date)
    return int(match.group(1)) if match is not None else None


def tag_date(date: str) -> str:
    """A date tag reduced to the day it names, inventing nothing it does not.

    A year stays a year, a year and month stay both; only what the tag states
    is kept, so an album that knows 1990 is never given a January it never
    claimed. The separator becomes a dash whatever the file used, so the two
    ways of writing one date stop being two different dates.

    What is dropped is the time, which in this library is padding rather than
    information. Keeping it puts `1990-05-01T12:00:00Z` in front of a person
    editing an album, which is not a date anybody reads.

    A shape not recognised is handed back as it came, cleaned of stray
    whitespace alone. Guessing at an unfamiliar tag would lose the only record
    of what the file actually says.
    """
    value = normalise(date)
    match = _TAG_DATE.match(value)
    if match is None:
        return value
    stated = (match.group("year"), match.group("month"), match.group("day"))
    return "-".join(part for part in stated if part is not None)


def is_various_artists(album_artist: str) -> bool:
    """True when an album artist names a compilation rather than a person."""
    return comparison_key(album_artist) in {
        comparison_key(VARIOUS_ARTISTS),
        "various",
        "va",
        "verschiedene",
    }
