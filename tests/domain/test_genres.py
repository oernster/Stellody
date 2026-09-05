"""The catalogue of genres an album can be stated to carry."""

from __future__ import annotations

import pytest

from stellody.domain import genres


class TestTheCatalogue:
    def test_it_holds_the_nineteen_that_were_settled(self) -> None:
        assert genres.GENRES == (
            "Alternative",
            "Blues",
            "Classical",
            "Comedy",
            "Dance",
            "Drum & Bass",
            "Electronic",
            "Folk",
            "Hip Hop",
            "Jazz",
            "Jungle",
            "Metal",
            "Pop",
            "Punk",
            "R&B & Soul",
            "Rock",
            "Soundtrack",
            "Trance",
            "World",
        )

    def test_it_is_alphabetical(self) -> None:
        assert list(genres.GENRES) == sorted(genres.GENRES)

    def test_no_name_appears_twice_however_it_is_cased(self) -> None:
        keys = [name.casefold() for name in genres.GENRES]
        assert len(set(keys)) == len(keys)

    def test_no_name_holds_the_separator_it_is_written_with(self) -> None:
        """Otherwise one stated value could not be read back as two genres."""
        for name in genres.GENRES:
            assert genres.SEPARATOR.strip() not in name


class TestReadingATagSomebodyElseWrote:
    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            # The shapes measured across the reference library.
            ("Pop", ("Pop",)),
            ("Hip-Hop/Rap", ("Hip-Hop", "Rap")),
            ("R&B/Soul", ("R&B", "Soul")),
            ("JUNGLE / FOOTWORK", ("JUNGLE", "FOOTWORK")),
            ("hip hop / rap", ("hip hop", "rap")),
            ("dance-house-progressive", ("dance-house-progressive",)),
            ("", ()),
            ("   ", ()),
        ],
    )
    def test_a_value_splits_into_its_pieces(
        self, value: str, expected: tuple[str, ...]
    ) -> None:
        assert genres.pieces_of(value) == expected

    def test_an_ampersand_never_splits_a_name(self) -> None:
        """Two catalogue names hold one, so splitting on it would break them."""
        assert genres.pieces_of("Drum & Bass") == ("Drum & Bass",)
        assert genres.pieces_of("R&B & Soul") == ("R&B & Soul",)

    def test_an_empty_piece_is_dropped(self) -> None:
        assert genres.pieces_of("Rock;;Pop") == ("Rock", "Pop")


class TestWhichBoxesATagTicks:
    def test_a_name_is_matched_whatever_its_case(self) -> None:
        assert genres.chosen_in("pop") == ("Pop",)
        assert genres.chosen_in("ROCK") == ("Rock",)

    def test_several_names_come_back_in_catalogue_order(self) -> None:
        assert genres.chosen_in("Rock; Alternative") == ("Alternative", "Rock")

    def test_a_name_holding_an_ampersand_is_matched_whole(self) -> None:
        assert genres.chosen_in("Drum & Bass") == ("Drum & Bass",)

    def test_nothing_is_inferred_from_a_name_that_merely_contains_one(
        self,
    ) -> None:
        """Ticking a box somebody did not tick leaves them unable to tell.

        `Progressive Rock` contains a catalogue name and resolves to nothing,
        because no ruling has been made about it. It is offered to the panel
        as an unmatched tag instead, which is visible. Contrast `Alternative
        Metal`, which reaches two genres because somebody said so rather than
        because the words are in it. `classical crossover` reaches Classical
        and Pop for that same reason; without the ruling it would have reached
        Classical alone by accident.
        """
        assert genres.chosen_in("Progressive Rock") == ()
        assert genres.chosen_in("Acid House") == ()

    def test_a_value_naming_nothing_in_the_catalogue_ticks_nothing(self) -> None:
        assert genres.chosen_in("Skiffle") == ()
        assert genres.chosen_in("") == ()


class TestWritingItDown:
    def test_the_order_is_the_catalogue_not_the_order_ticked(self) -> None:
        assert genres.stated_as(("Rock", "Alternative")) == "Alternative; Rock"
        assert genres.stated_as(("Alternative", "Rock")) == "Alternative; Rock"

    def test_nothing_ticked_states_nothing(self) -> None:
        assert genres.stated_as(()) == ""

    def test_one_genre_is_written_without_a_separator(self) -> None:
        assert genres.stated_as(("Pop",)) == "Pop"

    def test_a_name_offered_twice_is_written_once(self) -> None:
        assert genres.stated_as(("Pop", "Pop")) == "Pop"

    def test_a_name_not_in_the_catalogue_is_not_written(self) -> None:
        """The panel can only offer the catalogue, so this is a guard."""
        assert genres.stated_as(("Skiffle",)) == ""

    def test_what_is_written_reads_back_as_what_was_chosen(self) -> None:
        chosen = ("Alternative", "Drum & Bass", "R&B & Soul", "Rock")
        assert genres.chosen_in(genres.stated_as(chosen)) == chosen

    def test_every_name_survives_the_round_trip_on_its_own(self) -> None:
        for name in genres.GENRES:
            assert genres.chosen_in(genres.stated_as((name,))) == (name,)

    def test_every_name_at_once_survives_the_round_trip(self) -> None:
        assert genres.chosen_in(genres.stated_as(genres.GENRES)) == genres.GENRES


class TestTagsRuledToMeanAGenre:
    """Aliases are rulings, so each is settled here by name."""

    def test_heavy_metal_is_metal(self) -> None:
        """231 files, measured: the largest single unmatched tag."""
        assert genres.chosen_in("Heavy Metal") == ("Metal",)

    def test_hard_rock_is_rock(self) -> None:
        """20 files, measured."""
        assert genres.chosen_in("Hard Rock") == ("Rock",)

    def test_an_alias_is_matched_whatever_its_case(self) -> None:
        assert genres.chosen_in("HEAVY METAL") == ("Metal",)
        assert genres.chosen_in("heavy metal") == ("Metal",)

    def test_an_alias_inside_a_compound_tag_is_matched(self) -> None:
        assert genres.chosen_in("Heavy Metal/Hard Rock") == ("Metal", "Rock")

    def test_an_alias_beside_a_catalogue_name_gives_both(self) -> None:
        assert genres.chosen_in("Heavy Metal; Punk") == ("Metal", "Punk")

    def test_every_alias_names_genres_the_catalogue_offers(self) -> None:
        """An alias pointing at a name with no box could never be ticked."""
        for alias, named in genres.ALIASES.items():
            assert named, alias
            for name in named:
                assert name in genres.GENRES, alias

    def test_no_alias_is_keyed_on_a_catalogue_name(self) -> None:
        """That would let an alias quietly redirect a name to another box."""
        names = {name.casefold() for name in genres.GENRES}
        assert names.isdisjoint(genres.ALIASES)

    def test_every_alias_is_keyed_on_its_folded_form(self) -> None:
        """A key that is not folded can never be reached by the lookup."""
        for alias in genres.ALIASES:
            assert alias == alias.casefold()

    def test_an_alias_states_the_catalogue_name_not_the_tag(self) -> None:
        """What is written down is the genre, never the words the file used."""
        assert genres.stated_as(genres.chosen_in("Heavy Metal")) == "Metal"

    def test_the_hip_hop_tag_reaches_the_catalogue(self) -> None:
        """416 files, measured: `Hip-Hop` folds to a hyphen the name has not."""
        assert genres.chosen_in("Hip-Hop/Rap") == ("Hip Hop",)

    def test_the_unhyphenated_spelling_still_needs_no_alias(self) -> None:
        """35 files tagged `hip hop` match the catalogue name outright."""
        assert genres.chosen_in("hip hop") == ("Hip Hop",)
        assert genres.chosen_in("hip hop / rap") == ("Hip Hop",)

    def test_both_spellings_of_r_and_b_reach_soul(self) -> None:
        """39 files tagged `R&B`, 12 tagged `R&B/Soul`, measured."""
        assert genres.chosen_in("R&B") == ("R&B & Soul",)
        assert genres.chosen_in("R&B/Soul") == ("R&B & Soul",)

    def test_the_catalogue_name_itself_is_never_split_by_its_ampersands(
        self,
    ) -> None:
        assert genres.chosen_in("R&B & Soul") == ("R&B & Soul",)

    def test_a_tag_reaching_the_same_genre_twice_ticks_it_once(self) -> None:
        """`R&B/Soul` would otherwise name it through two separate pieces."""
        assert genres.stated_as(genres.chosen_in("R&B/Soul")) == "R&B & Soul"


class TestTheDanceSubTaxonomy:
    """56 files across four folders that reached nothing at all.

    One person's own `dance-<style>` and `house-<style>` naming, three albums
    and a single. Ruled to be Dance and Electronic together rather than given
    names of their own: the styles inside are distinctions between kinds of
    dance music, which is what carrying both names already says.
    """

    @pytest.mark.parametrize(
        "tag",
        (
            # `dance-trance` is deliberately absent: its style half names a
            # catalogue genre and was ruled to reach it, which the ruling
            # below states on its own.
            "house-melodic",
            "dance-house",
            "dance-house-progressive",
            "House",
            "house-progressive house",
            "dance-house-deep",
            "dance-house-acid",
            "dance-house-disco",
            "dance-electro",
        ),
    )
    def test_each_reaches_dance_and_electronic(self, tag: str) -> None:
        assert genres.chosen_in(tag) == ("Dance", "Electronic")

    def test_the_one_compound_value_reaches_them_through_its_other_half(
        self,
    ) -> None:
        """`minimal` names nothing and is left to, as an unknown word should
        be; the album still reaches the catalogue through the half that does.
        """
        assert genres.pieces_of("dance-house-tech / minimal") == (
            "dance-house-tech",
            "minimal",
        )
        assert genres.chosen_in("dance-house-tech / minimal") == (
            "Dance",
            "Electronic",
        )

    def test_the_plain_dance_tag_still_reaches_dance_alone(self) -> None:
        """432 files, measured: it names the genre outright and needs no ruling."""
        assert genres.chosen_in("dance") == ("Dance",)


class TestTheRulingsOnTheRest:
    def test_indie_dance_is_alternative_dance(self) -> None:
        """Oliver's ruling, 3 files: treated as alternative dance, so both."""
        assert genres.chosen_in("indie dance") == ("Alternative", "Dance")

    def test_dance_trance_also_reaches_trance(self) -> None:
        """Oliver's ruling, 16 files: the style half names a genre the
        catalogue already offers, so the album is findable under what it
        actually is."""
        assert genres.chosen_in("dance-trance") == ("Dance", "Electronic", "Trance")

    def test_techno_was_ruled_against_a_name_of_its_own(self) -> None:
        """3 files. Techno is a kind of electronic music, which the pair
        already says; naming every kind would make the catalogue a taxonomy
        rather than a list somebody can read."""
        assert "Techno" not in genres.GENRES
        assert genres.chosen_in("dance-techno") == ("Dance", "Electronic")

    def test_classical_crossover_is_classical_and_pop(self) -> None:
        """Oliver's ruling, 1 file: Alexis Ffrench's `Truth`, whose only other
        tagged track carries `pop`. Crossover is classical meeting popular
        music, so the pair says it without a name of its own."""
        assert genres.chosen_in("classical crossover") == ("Classical", "Pop")

    def test_britpop_is_a_subgenre_of_pop(self) -> None:
        """Oliver's ruling, 1 file: Kula Shaker on the compilation `K`."""
        assert genres.chosen_in("Britpop") == ("Pop",)

    def test_comedy_is_a_name_of_its_own_rather_than_an_alias(self) -> None:
        """1 file, The Lonely Island's `Incredibad`. Nothing else in the
        catalogue is near it, so it is offered rather than pointed elsewhere.
        """
        assert "Comedy" in genres.GENRES
        assert genres.chosen_in("Comedy") == ("Comedy",)
        assert "comedy" not in genres.ALIASES

    def test_alternative_metal_reaches_both(self) -> None:
        """6 files, measured. One tag naming two genres, ruled rather than
        guessed: a single-valued table could not have said it."""
        assert genres.chosen_in("Alternative Metal") == ("Alternative", "Metal")

    def test_a_tag_naming_two_genres_states_both(self) -> None:
        assert genres.stated_as(genres.chosen_in("Alternative Metal")) == (
            "Alternative; Metal"
        )

    def test_what_no_ruling_covers_is_still_left_alone(self) -> None:
        """Named so a later alias is a decision rather than an accident.

        These four were here once and have since been ruled on, which is what
        this test is for: a tag leaves the list by somebody deciding it does.
        No tag in the reference library reaches nothing any more, so what is
        named here is the half of a compound value that names no genre the
        catalogue holds, plus two strings the library does not carry at all.
        """
        for tag in ("minimal", "Progressive Rock", "Skiffle"):
            assert genres.chosen_in(tag) == (), tag

    def test_the_jungle_tag_reaches_the_catalogue_without_an_alias(self) -> None:
        """35 files carry `JUNGLE / FOOTWORK`, measured; they are three
        LTJ Bukem albums. The JUNGLE half names the genre outright once Jungle
        is in the catalogue, so no ruling is needed for it."""
        assert genres.chosen_in("JUNGLE / FOOTWORK") == ("Jungle",)

    def test_footwork_is_not_quietly_made_to_mean_something(self) -> None:
        """It is a real genre and it is not what those records are, so the
        word reaches nothing rather than being folded into Jungle."""
        assert genres.chosen_in("Footwork") == ()
        assert "footwork" not in genres.ALIASES
