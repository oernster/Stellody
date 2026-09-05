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
        R&B. Comedy is a main rather than Discogs' Non-Music. Country and
        Reggae carry no tag at all and are offered on a ruling, which is the
        ground Punk stands on."""
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


class TestTagsRuledToMeanAGenre:
    """Aliases are rulings, so each is settled here by name."""

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

    def test_an_alias_is_matched_whatever_its_case(self) -> None:
        assert genres.chosen_in("DANCE") == ("Electronic",)
        assert genres.chosen_in("dance") == ("Electronic",)

    def test_the_hip_hop_tag_reaches_the_catalogue(self) -> None:
        """415 files carry `Hip-Hop/Rap` and 26 `hip hop / rap`, measured."""
        assert genres.chosen_in("Hip-Hop/Rap") == ("Hip Hop",)
        assert genres.chosen_in("hip hop / rap") == ("Hip Hop",)

    def test_the_unhyphenated_spelling_needs_no_alias(self) -> None:
        """35 files tagged `hip hop` match the catalogue name outright."""
        assert genres.chosen_in("hip hop") == ("Hip Hop",)

    def test_the_bare_dance_tag_states_electronic_and_no_more(self) -> None:
        """873 files. Discogs has no Dance style and one is not invented to
        hold a tag that says no more than electronic."""
        assert genres.chosen_in("dance") == ("Electronic",)

    def test_alternative_alone_is_the_rock_kind(self) -> None:
        """479 files, every one of them a rock record."""
        assert genres.chosen_in("Alternative") == ("Rock", "Alternative Rock")

    def test_the_r_and_b_tag_is_the_modern_kind(self) -> None:
        """39 files tagged `R&B` and 10 `R&B/Soul`, ruled by Oliver. Neither
        is funk and neither is soul, which are mains of their own."""
        assert genres.chosen_in("R&B") == ("Contemporary R&B",)
        assert genres.chosen_in("R&B/Soul") == ("Contemporary R&B",)

    def test_the_world_tag_is_a_name_rather_than_a_ruling_now(self) -> None:
        """20 files. It was an alias while Discogs' umbrella held it."""
        assert genres.chosen_in("World") == ("World",)


class TestTheDanceSubTaxonomy:
    """56 files across four folders that reached nothing before this.

    One person's own `dance-<style>` and `house-<style>` naming, three albums
    and a single. Each names its style outright now the catalogue has two
    levels; each states Electronic through it.
    """

    @pytest.mark.parametrize(
        ("tag", "style"),
        (
            ("dance-trance", "Trance"),
            ("dance-techno", "Techno"),
            ("dance-house", "House"),
            ("house-melodic", "House"),
            ("House", "House"),
            ("indie dance", "House"),
            ("dance-house-progressive", "Progressive House"),
            ("house-progressive house", "Progressive House"),
            ("dance-house-deep", "Deep House"),
            ("dance-house-acid", "Acid House"),
            ("dance-house-disco", "Disco"),
            ("dance-electro", "Electro"),
        ),
    )
    def test_each_reaches_its_style_and_electronic(self, tag: str, style: str) -> None:
        assert genres.chosen_in(tag) == ("Electronic", style)

    def test_the_one_compound_value_reaches_through_its_other_half(self) -> None:
        """`minimal` names nothing and is left to, as an unknown word should
        be; the album still reaches the catalogue through the half that does.
        """
        assert genres.chosen_in("dance-house-tech / minimal") == (
            "Electronic",
            "Tech House",
        )


class TestTheRulingsOnTheRest:
    def test_britpop_is_a_rock_style(self) -> None:
        """1 file, Kula Shaker on the compilation `K`. Ruled to follow where
        Discogs files it rather than the earlier flat-list reading of Pop."""
        assert genres.chosen_in("Britpop") == ("Rock", "Britpop")

    def test_indie_dance_is_house(self) -> None:
        """3 files on Helsloot's `Never Tried`, whose other tags are house.
        Discogs has no Indie Dance style to reach for."""
        assert genres.chosen_in("indie dance") == ("Electronic", "House")

    def test_classical_crossover_is_classical_and_pop(self) -> None:
        """1 file, Alexis Ffrench's `Truth`, whose only other tagged track
        carries `pop`. Crossover is classical meeting popular music."""
        assert genres.chosen_in("classical crossover") == ("Classical", "Pop")

    def test_comedy_is_a_main_of_its_own(self) -> None:
        """1 file, The Lonely Island's `Incredibad`. Discogs hangs Comedy under
        Non-Music, a heading for spoken word and field recordings; ruled by
        Oliver that the record is music, so it is not filed under a name saying
        it is not. The one place this catalogue leaves Discogs' shape."""
        assert genres.chosen_in("Comedy") == ("Comedy",)

    def test_the_heading_it_used_to_hang_under_still_reads_back(self) -> None:
        assert genres.chosen_in("Non-Music") == ("Comedy",)


class TestNamesTheCatalogueUsedToCarry:
    """A genre stated before the second level still reads back as meant.

    These were catalogue names when the list was flat, so a value written then
    holds them; they are aliases now rather than names.
    """

    @pytest.mark.parametrize(
        ("stored", "expected"),
        (
            ("Metal", ("Rock", "Heavy Metal")),
            ("R&B & Soul", ("Contemporary R&B",)),
            ("Drum & Bass", ("Electronic", "Drum n Bass")),
            ("Stage & Screen", ("Soundtrack",)),
            ("Modern Classical", ("Classical",)),
            ("Jungle", ("Electronic", "Jungle")),
            ("Punk", ("Rock", "Punk")),
        ),
    )
    def test_it_still_reads_back(self, stored: str, expected: tuple[str, ...]) -> None:
        assert genres.chosen_in(stored) == expected
