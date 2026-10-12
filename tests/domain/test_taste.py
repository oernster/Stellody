"""Taste profiles' rules, with nothing installed. `DISCOVERY.md` FR-D87 to FR-D93."""

from __future__ import annotations

from stellody.domain.taste import (
    TasteProfile,
    holding,
    named,
    ordered,
    saved,
    usable_name,
    without,
)

AMBIENT = TasteProfile("Ambient", ("Ambient",))
JAZZ = TasteProfile("Jazz", ("Jazz", "Blues"))
ROCK = TasteProfile("rock", ("Rock",))


class TestTheList:
    def test_it_is_alphabetical_ignoring_case(self) -> None:
        """FR-D88: "rock", "Ambient", "Jazz" read Ambient, Jazz, rock."""
        assert ordered((ROCK, AMBIENT, JAZZ)) == (AMBIENT, JAZZ, ROCK)


class TestWhatCountsAsTheSameSelection:
    def test_the_order_genres_were_ticked_in_does_not_matter(self) -> None:
        assert holding((JAZZ,), ("Blues", "Jazz")) is JAZZ

    def test_one_genre_more_or_fewer_is_a_new_selection(self) -> None:
        assert holding((JAZZ,), ("Jazz",)) is None
        assert holding((JAZZ,), ("Jazz", "Blues", "Soul")) is None

    def test_no_profiles_hold_nothing(self) -> None:
        assert holding((), ("Jazz",)) is None


class TestNames:
    def test_a_blank_name_is_no_name(self) -> None:
        assert usable_name("   ") is None
        assert usable_name("") is None

    def test_a_name_is_trimmed(self) -> None:
        assert usable_name("  Late night  ") == "Late night"

    def test_names_are_one_name_whatever_their_case(self) -> None:
        assert named((JAZZ,), " jazz ") is JAZZ
        assert named((JAZZ,), "Soul") is None


class TestSavingAndDeleting:
    def test_saving_a_taken_name_replaces_that_profile(self) -> None:
        """FR-D91: one profile named "jazz", holding the new genres."""
        after = saved((AMBIENT, JAZZ), "jazz", ("Jazz", "Soul"))
        assert after == (AMBIENT, TasteProfile("jazz", ("Jazz", "Soul")))

    def test_saving_a_new_name_adds_it_in_order(self) -> None:
        after = saved((AMBIENT, ROCK), " Jazz ", ("Jazz",))
        assert [profile.name for profile in after] == ["Ambient", "Jazz", "rock"]

    def test_deleting_takes_out_that_profile_alone(self) -> None:
        """FR-D92."""
        assert without((AMBIENT, JAZZ), "JAZZ") == (AMBIENT,)
        assert without((AMBIENT,), "Jazz") == (AMBIENT,)
