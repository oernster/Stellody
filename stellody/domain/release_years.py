"""Which years the music a run offers was released in. FR-D58 to FR-D62.

Pure: no I/O, no framework, no clock. The current year arrives as an argument,
since what counts as a plausible year moves with it and the domain never reads
the time itself.

**The years scope what a run offers, never what it learns from.** Nothing here
is consulted when choosing whose records to ask about; it is consulted only
about what came back. That distinction is the whole feature, so it is stated
where the rule lives rather than left to be inferred from who calls it.

**A year that cannot be established does not fit.** A release group stating no
date is common (10 of 61 for one artist, measured on 2026-09-26), so with years
set such a record is left out rather than given a year it never claimed.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum

# The earliest year a range may name. Ruled by Oliver on 2026-09-26: earlier
# years exist in the catalogue in principle and in almost nothing in practice,
# so a range reaching back past this is far likelier to be a slip of a key.
FIRST_YEAR = 1900
# How far past the current year a range may reach, so a record already
# announced for next year can be asked about.
YEARS_AHEAD = 1
# What a year looks like when typed: four plain digits, nothing else.
_TYPED_YEAR = re.compile(r"\d{4}", re.ASCII)


@dataclass(frozen=True, slots=True)
class ReleaseYears:
    """The years a run may offer music from; either bound may be absent.

    Both bounds included. No bounds at all is every year, which is what a run
    asked no question about years has always done.
    """

    earliest: int | None = None
    latest: int | None = None

    def __post_init__(self) -> None:
        if (
            self.earliest is not None
            and self.latest is not None
            and self.earliest > self.latest
        ):
            raise ValueError("the earliest year is later than the latest")

    @property
    def is_bounded(self) -> bool:
        """True where either bound is set, so the years say anything at all."""
        return self.earliest is not None or self.latest is not None

    def admits(self, year: int | None) -> bool:
        """Whether a record released in this year may be offered.

        Every year, including none, where nothing is bounded. Otherwise a
        record with no year is refused, since it cannot be shown to fit.
        """
        if not self.is_bounded:
            return True
        if year is None:
            return False
        if self.earliest is not None and year < self.earliest:
            return False
        return self.latest is None or year <= self.latest


# Every year, which is what a run with no years set asks for.
ANY_YEAR = ReleaseYears()


class Bound(StrEnum):
    """Which of the two fields a refusal is about."""

    EARLIEST = "earliest"
    LATEST = "latest"


class YearFault(StrEnum):
    """Why typed years cannot be used."""

    NOT_A_YEAR = "not-a-year"
    TOO_EARLY = "too-early"
    TOO_LATE = "too-late"
    REVERSED = "reversed"


@dataclass(frozen=True, slots=True)
class YearRefusal:
    """Typed years that cannot be used, with which field and why. FR-D59."""

    bound: Bound
    fault: YearFault


def last_year(this_year: int) -> int:
    """The latest year a range may name, read from the current one."""
    return this_year + YEARS_AHEAD


def _typed(text: str, bound: Bound, this_year: int) -> int | None | YearRefusal:
    """One field read: its year, None where empty, else why it will not do."""
    stated = text.strip()
    if not stated:
        return None
    if not _TYPED_YEAR.fullmatch(stated):
        return YearRefusal(bound, YearFault.NOT_A_YEAR)
    year = int(stated)
    if year < FIRST_YEAR:
        return YearRefusal(bound, YearFault.TOO_EARLY)
    if year > last_year(this_year):
        return YearRefusal(bound, YearFault.TOO_LATE)
    return year


def read_years(
    earliest: str, latest: str, this_year: int
) -> ReleaseYears | YearRefusal:
    """The years two typed fields ask for; else the first reason they cannot.

    Nothing is corrected. A year out of range or the wrong way round is
    refused and said, since a range quietly adjusted answers a question
    nobody asked.
    """
    first = _typed(earliest, Bound.EARLIEST, this_year)
    if isinstance(first, YearRefusal):
        return first
    last = _typed(latest, Bound.LATEST, this_year)
    if isinstance(last, YearRefusal):
        return last
    if first is not None and last is not None and first > last:
        return YearRefusal(Bound.EARLIEST, YearFault.REVERSED)
    return ReleaseYears(earliest=first, latest=last)
