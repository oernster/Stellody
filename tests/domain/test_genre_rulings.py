"""What a tag means, one ruling at a time.

Aliases are rulings rather than rules: the table grows only when somebody says
a particular tag means a particular genre. Nothing is inferred from a name
merely holding another, so every entry is settled here by name with the count
that weighed it.

Held apart from `test_genres`, which is about the catalogue's own shape and how
a value is read and written. This is about the library's own words.
"""

from __future__ import annotations

import pytest

from stellody.domain import genres


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
    def test_britpop_is_a_pop_style(self) -> None:
        """1 file, Kula Shaker on the compilation `K`. Discogs files it under
        Rock; ruled by Oliver that a kind of pop belongs under Pop."""
        assert genres.chosen_in("Britpop") == ("Pop", "Britpop")

    def test_rap_stands_beside_hip_hop(self) -> None:
        """Discogs makes it a style of Hip Hop. Ruled a main: the two are used
        as separate genres far more often than that filing suggests."""
        assert genres.chosen_in("Rap") == ("Rap",)

    def test_the_hip_hop_slash_rap_tag_still_means_the_one_genre(self) -> None:
        """415 files, ruled Hip Hop before Rap was a name here. The ruling is
        what it reads by, so a new name beside it changes nothing."""
        assert genres.chosen_in("Hip-Hop/Rap") == ("Hip Hop",)

    def test_punk_answers_to_nothing_above_it(self) -> None:
        """Discogs hangs it under Rock. Ruled a main of its own, so asking for
        rock no longer hands somebody every punk record."""
        assert genres.chosen_in("Punk") == ("Punk",)

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
            ("Punk", ("Punk",)),
        ),
    )
    def test_it_still_reads_back(self, stored: str, expected: tuple[str, ...]) -> None:
        assert genres.chosen_in(stored) == expected
