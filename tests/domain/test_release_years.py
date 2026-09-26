"""The years a run may offer music from. FR-D58 to FR-D62."""

from __future__ import annotations

import pytest

from stellody.domain.discovery import ReleaseGroup, albums_missing, everything_offered
from stellody.domain.release_years import (
    ANY_YEAR,
    FIRST_YEAR,
    Bound,
    ReleaseYears,
    YearFault,
    YearRefusal,
    last_year,
    read_years,
)

THIS_YEAR = 2026
EIGHTIES = ReleaseYears(1980, 1989)
ROCK = ("Rock",)


def album(title: str, released: str) -> ReleaseGroup:
    """An album first released on this date, as a catalogue states it."""
    return ReleaseGroup(title=title, released=released)


class TestAdmitting:
    def test_no_bounds_admits_every_year_and_none(self) -> None:
        assert not ANY_YEAR.is_bounded
        assert ANY_YEAR.admits(1850)
        assert ANY_YEAR.admits(None)

    def test_a_lower_bound_alone(self) -> None:
        after = ReleaseYears(earliest=2020)
        assert after.admits(2020)
        assert after.admits(2030)
        assert not after.admits(2019)

    def test_an_upper_bound_alone(self) -> None:
        before = ReleaseYears(latest=1989)
        assert before.admits(1989)
        assert before.admits(1950)
        assert not before.admits(1990)

    def test_both_bounds_are_inclusive(self) -> None:
        assert EIGHTIES.admits(1980)
        assert EIGHTIES.admits(1989)
        assert not EIGHTIES.admits(1979)
        assert not EIGHTIES.admits(1990)

    def test_no_year_does_not_fit_a_bounded_range(self) -> None:
        """FR-D62: a year is never invented to make a record fit."""
        assert not EIGHTIES.admits(None)

    def test_a_reversed_range_cannot_be_built(self) -> None:
        with pytest.raises(ValueError):
            ReleaseYears(1990, 1980)


class TestReadingTypedYears:
    def test_both_empty_is_every_year(self) -> None:
        assert read_years("", "  ", THIS_YEAR) == ANY_YEAR

    def test_either_bound_may_be_left_empty(self) -> None:
        assert read_years("2020", "", THIS_YEAR) == ReleaseYears(earliest=2020)
        assert read_years("", "1979", THIS_YEAR) == ReleaseYears(latest=1979)

    def test_a_closed_range(self) -> None:
        assert read_years("1980", "1989", THIS_YEAR) == EIGHTIES

    def test_the_same_year_twice_is_one_year(self) -> None:
        assert read_years("1985", "1985", THIS_YEAR) == ReleaseYears(1985, 1985)

    @pytest.mark.parametrize("typed", ["198", "19850", "abcd", "19 5", "١٩٨٥"])
    def test_anything_but_four_digits_is_not_a_year(self, typed: str) -> None:
        assert read_years(typed, "", THIS_YEAR) == YearRefusal(
            Bound.EARLIEST, YearFault.NOT_A_YEAR
        )

    def test_the_first_year_is_allowed_and_the_one_before_is_not(self) -> None:
        assert read_years(str(FIRST_YEAR), "", THIS_YEAR) == ReleaseYears(FIRST_YEAR)
        assert read_years(str(FIRST_YEAR - 1), "", THIS_YEAR) == YearRefusal(
            Bound.EARLIEST, YearFault.TOO_EARLY
        )

    def test_next_year_is_allowed_and_the_one_after_is_not(self) -> None:
        """The ceiling follows the year handed in rather than a written one."""
        ceiling = last_year(THIS_YEAR)
        assert ceiling == THIS_YEAR + 1
        assert read_years("", str(ceiling), THIS_YEAR) == ReleaseYears(latest=ceiling)
        assert read_years("", str(ceiling + 1), THIS_YEAR) == YearRefusal(
            Bound.LATEST, YearFault.TOO_LATE
        )

    def test_a_reversed_range_is_refused_not_swapped(self) -> None:
        assert read_years("1990", "1980", THIS_YEAR) == YearRefusal(
            Bound.EARLIEST, YearFault.REVERSED
        )

    def test_the_from_field_is_reported_first(self) -> None:
        assert read_years("x", "y", THIS_YEAR).bound is Bound.EARLIEST


class TestAnAlbumsYear:
    @pytest.mark.parametrize("released", ["1985", "1985-07", "1985-07-30"])
    def test_every_shape_the_catalogue_states_gives_the_year(
        self, released: str
    ) -> None:
        assert album("Hounds of Love", released).year == 1985

    def test_no_date_is_no_year(self) -> None:
        assert album("The Early Years", "").year is None


class TestOfferingByYear:
    def test_only_albums_inside_the_years_are_missing(self) -> None:
        offered = (
            album("Before", "1979-12-31"),
            album("First", "1980"),
            album("Last", "1989-12"),
            album("After", "1990"),
            album("Undated", ""),
        )
        kept = albums_missing(frozenset(), offered, ROCK, EIGHTIES)
        assert [group.title for group in kept] == ["First", "Last"]

    def test_no_years_keeps_the_undated(self) -> None:
        kept = albums_missing(frozenset(), (album("Undated", ""),), ROCK)
        assert [group.title for group in kept] == ["Undated"]

    def test_an_owned_album_inside_the_years_is_still_not_offered(self) -> None:
        owned = album("Owned", "1985")
        kept = albums_missing(frozenset({owned.match}), (owned,), ROCK, EIGHTIES)
        assert kept == ()

    def test_a_candidates_discography_keeps_to_the_years(self) -> None:
        released = (album("Old", "1975"), album("New", "2022"))
        kept = everything_offered(released, ReleaseYears(earliest=2020))
        assert [group.title for group in kept] == ["New"]
