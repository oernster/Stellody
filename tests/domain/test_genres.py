"""The catalogue of genres an album can be stated to carry.

Two levels: main categories with styles under them, taking Discogs' shape and
Discogs' spellings, curated to what this library holds. A style states its
main, so one tick says the specific thing and the general thing at once.
"""

from __future__ import annotations

import pytest

from stellody.domain import genres


class TestTheCatalogue:
    def test_it_holds_the_mains_that_were_settled(self) -> None:
        """Discogs' vocabulary, on Oliver's rulings rather than Discogs' tree.
        Brass & Military, Children's, Latin and Non-Music hold nothing here.
        A main that held one style is that style's name instead, so Stage &
        Screen is Soundtrack; Classical swallowed Modern Classical the other
        way round, since 175 files say Classical and none says Modern. The two
        umbrella names that said three things and two things are their parts:
        Folk, World and Country stand alone, as do Funk, Soul and Contemporary
        R&B. Comedy is a main rather than Discogs' Non-Music; Punk answers to
        nothing above it rather than sitting under Rock; Rap stands beside Hip
        Hop rather than under it. Country, Punk and
        Reggae carry no tag at all and are offered on a ruling."""
        assert genres.MAINS == (
            "Blues",
            "Classical",
            "Comedy",
            "Contemporary R&B",
            "Country",
            "Electronic",
            "Folk",
            "Funk",
            "Hip Hop",
            "Jazz",
            "Pop",
            "Punk",
            "Rap",
            "Reggae",
            "Rock",
            "Soul",
            "Soundtrack",
            "World",
        )

    def test_the_mains_are_alphabetical(self) -> None:
        assert list(genres.MAINS) == sorted(genres.MAINS)

    def test_every_main_lists_its_styles_alphabetically(self) -> None:
        for main, styles in genres.CATALOGUE:
            assert list(styles) == sorted(styles), main

    def test_the_order_offered_is_each_main_then_its_own_styles(self) -> None:
        expected: list[str] = []
        for main, styles in genres.CATALOGUE:
            expected.append(main)
            expected.extend(styles)
        assert list(genres.GENRES) == expected

    def test_no_name_appears_twice_anywhere_in_the_tree(self) -> None:
        """A stored value is read back by name, so one name must mean one
        place; a style under two mains could not be read back at all."""
        keys = [name.casefold() for name in genres.GENRES]
        assert len(set(keys)) == len(keys)

    def test_every_style_knows_its_main(self) -> None:
        styles = [style for _main, styles in genres.CATALOGUE for style in styles]
        assert sorted(genres.MAIN_OF) == sorted(styles)
        assert set(genres.MAIN_OF.values()) <= set(genres.MAINS)

    def test_no_main_is_also_a_style(self) -> None:
        assert set(genres.MAINS).isdisjoint(genres.MAIN_OF)

    def test_no_name_holds_the_separator_it_is_written_with(self) -> None:
        """Otherwise one stated value could not be read back as two genres."""
        for name in genres.GENRES:
            assert genres.SEPARATOR.strip() not in name

    def test_footwork_is_not_offered(self) -> None:
        """A real Discogs style; the wrong word on the only records here that
        carry it, so it is left out rather than aliased away."""
        assert "Footwork" not in genres.GENRES


class TestReadingATagSomebodyElseWrote:
    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            ("Pop", ("Pop",)),
            ("Rock; Pop", ("Rock", "Pop")),
            ("dance-house-progressive", ("dance-house-progressive",)),
            ("", ()),
            ("   ", ()),
        ],
    )
    def test_a_value_splits_into_its_pieces(
        self, value: str, expected: tuple[str, ...]
    ) -> None:
        assert genres.pieces_of(value) == expected

    def test_nothing_but_the_semicolon_splits_a_value(self) -> None:
        """Catalogue names hold an ampersand, a solidus and a comma between
        them, so splitting on any of those would break the names themselves.
        The comma was split on once and broke `Folk, World, & Country`, which
        the catalogue no longer carries, into pieces that matched other names;
        no file tag in the library holds a comma at all. The rule stands with
        the name gone, since a tag somebody else wrote may still hold one.
        """
        assert genres.pieces_of("Drum n Bass") == ("Drum n Bass",)
        assert genres.pieces_of("Funk / Soul") == ("Funk / Soul",)
        assert genres.pieces_of("Folk, World, & Country") == ("Folk, World, & Country",)

    def test_an_empty_piece_is_dropped(self) -> None:
        assert genres.pieces_of("Rock;;Pop") == ("Rock", "Pop")


class TestWhichBoxesATagTicks:
    def test_a_name_is_matched_whatever_its_case(self) -> None:
        assert genres.chosen_in("pop") == ("Pop",)
        assert genres.chosen_in("ROCK") == ("Rock",)

    def test_several_names_come_back_in_catalogue_order(self) -> None:
        assert genres.chosen_in("Pop; Blues") == ("Blues", "Pop")

    def test_a_name_holding_an_ampersand_is_matched_whole(self) -> None:
        assert genres.chosen_in("Drum n Bass") == ("Electronic", "Drum n Bass")

    def test_a_name_holding_a_solidus_is_matched_whole(self) -> None:
        """`Hip Hop / Rap` is one ruling rather than two halves asked apart."""
        assert genres.chosen_in("Hip Hop / Rap") == ("Hip Hop",)

    def test_the_old_umbrella_over_funk_and_soul_reaches_both(self) -> None:
        """Nothing matches `Funk / Soul` whole now that the umbrella is gone,
        so it splits and both halves land, which is what it says."""
        assert genres.chosen_in("Funk / Soul") == ("Funk", "Soul")

    def test_a_compound_tag_is_split_on_its_solidus_when_nothing_matches(
        self,
    ) -> None:
        """Which is how `JUNGLE / FOOTWORK` reaches Jungle: the whole value
        names nothing, so each half is asked in turn."""
        assert genres.chosen_in("JUNGLE / FOOTWORK") == ("Electronic", "Jungle")

    def test_nothing_is_inferred_from_a_name_that_merely_contains_one(
        self,
    ) -> None:
        """Ticking a box somebody did not tick leaves them unable to tell.

        `Progressive Rock` contains a catalogue name and reaches nothing,
        because nobody has ruled on it. Contrast `classical crossover`, which
        reaches Classical and Pop because somebody said so rather than because
        the word Classical is in it.
        """
        assert genres.chosen_in("Progressive Rock") == ()
        assert genres.chosen_in("Acid Jazz") == ()

    def test_a_value_naming_nothing_in_the_catalogue_ticks_nothing(self) -> None:
        assert genres.chosen_in("Skiffle") == ()
        assert genres.chosen_in("") == ()


class TestAStyleStatesItsMain:
    def test_a_style_brings_its_main_with_it(self) -> None:
        """An album marked Trance IS electronic, so a filter for Electronic
        has to find it without being told what the kinds of it are."""
        assert genres.chosen_in("Trance") == ("Electronic", "Trance")

    def test_a_main_can_be_stated_on_its_own(self) -> None:
        """For a record that is electronic and nothing more specific."""
        assert genres.chosen_in("Electronic") == ("Electronic",)

    def test_the_main_comes_first_because_the_catalogue_offers_it_first(
        self,
    ) -> None:
        assert genres.chosen_in("Heavy Metal") == ("Rock", "Heavy Metal")

    def test_two_styles_of_one_main_bring_it_once(self) -> None:
        assert genres.chosen_in("Trance; House") == ("Electronic", "House", "Trance")

    def test_with_mains_adds_nothing_to_a_main_alone(self) -> None:
        assert genres.with_mains(("Pop",)) == ("Pop",)

    def test_writing_a_style_writes_its_main_too(self) -> None:
        """The stored value says both things the tick meant, so nothing has
        to re-derive the main every time the value is read."""
        assert genres.stated_as(("Trance",)) == "Electronic; Trance"


class TestWritingItDown:
    def test_the_order_is_the_catalogue_not_the_order_ticked(self) -> None:
        assert genres.stated_as(("Pop", "Blues")) == "Blues; Pop"
        assert genres.stated_as(("Blues", "Pop")) == "Blues; Pop"

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
        chosen = ("Blues", "Electronic", "Trance", "Pop")
        assert genres.chosen_in(genres.stated_as(chosen)) == (
            "Blues",
            "Electronic",
            "Trance",
            "Pop",
        )

    def test_every_name_survives_the_round_trip_on_its_own(self) -> None:
        for name in genres.GENRES:
            assert genres.chosen_in(genres.stated_as((name,))) == genres.with_mains(
                (name,)
            )

    def test_every_name_at_once_survives_the_round_trip(self) -> None:
        assert genres.chosen_in(genres.stated_as(genres.GENRES)) == genres.GENRES
