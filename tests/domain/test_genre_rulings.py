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
        """That would let an alias quietly redirect a name to another box.

        Matching ignores case, so a name in any case is that name and nothing
        else: ruled by Oliver on 2026-10-01, which retired the one exception,
        `dance` read as Electronic."""
        names = {name.casefold() for name in genres.GENRES}
        assert not names & set(genres.ALIASES)

    def test_every_catalogue_name_in_its_own_spelling_reads_back_as_itself(
        self,
    ) -> None:
        """What a ticked box writes must read back as that box, ruling or no."""
        for name in genres.GENRES:
            assert name in genres.chosen_in(name), name

    def test_the_rulings_still_answer_from_where_they_always_did(self) -> None:
        """Moved to their own module on 2026-10-01; one table, two addresses."""
        from stellody.domain import genre_rulings

        assert genres.ALIASES is genre_rulings.ALIASES

    def test_every_alias_is_keyed_on_its_folded_form(self) -> None:
        """A key that is not folded can never be reached by the lookup."""
        for alias in genres.ALIASES:
            assert alias == alias.casefold()

    def test_an_alias_is_matched_whatever_its_case(self) -> None:
        assert genres.chosen_in("ALTERNATIVE") == ("Rock", "Alternative Rock")
        assert genres.chosen_in("alternative") == ("Rock", "Alternative Rock")

    def test_the_hip_hop_tag_reaches_the_catalogue(self) -> None:
        """415 files carry `Hip-Hop/Rap` and 26 `hip hop / rap`, measured."""
        assert genres.chosen_in("Hip-Hop/Rap") == ("Hip Hop",)
        assert genres.chosen_in("hip hop / rap") == ("Hip Hop",)

    def test_the_unhyphenated_spelling_needs_no_alias(self) -> None:
        """35 files tagged `hip hop` match the catalogue name outright."""
        assert genres.chosen_in("hip hop") == ("Hip Hop",)

    def test_the_bare_dance_tag_is_the_dance_main_in_any_case(self) -> None:
        """873 files. Read as Electronic until Dance became a main; ruled by
        Oliver on 2026-10-01 to be Dance, whatever its case."""
        for spelling in ("dance", "DANCE", "Dance"):
            assert genres.chosen_in(spelling) == ("Dance",), spelling

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
    levels; each states that style's main through it. Since Electronic was
    split on 2026-10-01 (FR-D77) the main is House, Techno & Electro or Dance.
    """

    @pytest.mark.parametrize(
        ("tag", "expected"),
        (
            ("dance-trance", ("Techno & Electro", "Trance")),
            ("dance-techno", ("Techno & Electro", "Techno")),
            ("dance-electro", ("Techno & Electro", "Electro")),
            ("dance-house", ("House",)),
            ("house-melodic", ("House",)),
            ("House", ("House",)),
            ("indie dance", ("House",)),
            ("dance-house-progressive", ("House", "Progressive House")),
            ("house-progressive house", ("House", "Progressive House")),
            ("dance-house-deep", ("House", "Deep House")),
            ("dance-house-acid", ("House", "Acid House")),
            ("dance-house-disco", ("Dance", "Disco")),
        ),
    )
    def test_each_reaches_its_style_and_main(
        self, tag: str, expected: tuple[str, ...]
    ) -> None:
        assert genres.chosen_in(tag) == expected

    def test_the_one_compound_value_reaches_through_its_other_half(self) -> None:
        """`minimal` names nothing and is left to, as an unknown word should
        be; the album still reaches the catalogue through the half that does.
        """
        assert genres.chosen_in("dance-house-tech / minimal") == (
            "House",
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
        assert genres.chosen_in("indie dance") == ("House",)

    def test_electro_house_is_house(self) -> None:
        """Stated by MusicBrainz for James Egbert and Noisia, who were withheld
        from a house run as Electronic alone; Dirtyloud was offered nobody.
        House is a main since 2026-10-01, so it states that alone."""
        assert genres.chosen_in("electro house") == ("House",)

    def test_ambient_techno_is_techno(self) -> None:
        """Stated by MusicBrainz for The Field and four more, withheld from a
        techno run until this was ruled."""
        assert genres.chosen_in("ambient techno") == ("Techno & Electro", "Techno")

    @pytest.mark.parametrize(
        ("stated", "expected"),
        (
            ("drum and bass", ("Electronic", "Drum n Bass")),
            ("liquid funk", ("Electronic", "Drum n Bass")),
            ("vocal trance", ("Techno & Electro", "Trance")),
            ("indie rock", ("Rock", "Alternative Rock")),
            ("indie pop", ("Pop", "Indie Pop")),
            ("dubstep", ("Electronic", "Dubstep")),
            ("uk garage", ("Electronic", "UK Garage")),
            ("trip hop", ("Dance", "Downtempo")),
            ("electronica", ("Dance", "Electronica")),
            ("downtempo", ("Dance", "Downtempo")),
            ("ambient", ("Electronic", "Ambient")),
            ("indietronica", ("Dance", "Electronica")),
        ),
    )
    def test_the_names_a_filter_withheld_on_2026_09_30(
        self, stated: str, expected: tuple[str, ...]
    ) -> None:
        """74 similar artists stated only names nothing here recognised; ruled
        by Oliver. Those once ruled Electronic alone have a style of their own
        since 2026-10-01 (FR-D77), so they still stay out of a House or Techno
        filter while a filter for their own style keeps them."""
        assert genres.chosen_in(stated) == expected


class TestTheRulingsOf2026_10_01:
    """FR-D77: 155 of 1,996 similar artists in Oliver's whole-library answer
    stated only names nothing here recognised. Each name below was ruled."""

    @pytest.mark.parametrize(
        ("stated", "expected"),
        (
            ("edm", ("Dance", "EDM")),
            ("eurodance", ("Dance", "Eurodance")),
            ("big beat", ("Electronic", "Big Beat")),
            ("italo dance", ("Dance", "Italo Dance")),
            ("dance-pop", ("Dance", "Dance-Pop")),
            ("hi-nrg", ("Dance", "Hi-NRG")),
            ("nu skool breaks", ("Dance", "Breakbeat")),
            ("breakbeat hardcore", ("Dance", "Breakbeat")),
            ("future bass", ("Dance", "EDM")),
            ("trap edm", ("Dance", "EDM")),
            ("rave", ("Dance",)),
            ("club", ("Dance",)),
            ("new rave", ("Dance",)),
            ("minimal techno", ("Techno & Electro", "Minimal Techno")),
            ("ebm", ("Techno & Electro", "EBM")),
            ("electro-industrial", ("Techno & Electro", "EBM")),
            ("aggrotech", ("Techno & Electro", "EBM")),
            ("witch house", ("Electronic",)),
            ("detroit techno", ("Techno & Electro", "Techno")),
            ("microhouse", ("House",)),
            ("hip house", ("House",)),
            ("euro house", ("House",)),
            ("goa trance", ("Techno & Electro", "Trance")),
            ("electroclash", ("Techno & Electro", "Electro")),
            ("synth-pop", ("Pop", "Synth-pop")),
            ("synthpop", ("Pop", "Synth-pop")),
            ("futurepop", ("Pop", "Synth-pop")),
            ("bitpop", ("Pop", "Electropop")),
            ("new wave", ("Pop", "New Wave")),
            ("dream pop", ("Pop", "Dream Pop")),
            ("k-pop", ("Pop", "K-Pop")),
            ("pop rock", ("Pop", "Pop Rock")),
            ("psychedelic pop", ("Pop",)),
            ("folk pop", ("Pop",)),
            ("death metal", ("Rock", "Heavy Metal")),
            ("mathcore", ("Rock", "Heavy Metal")),
            ("post-punk", ("Punk",)),
            ("psychobilly", ("Punk",)),
            ("acid jazz", ("Jazz",)),
            ("lounge", ("Jazz",)),
            ("mpb", ("World",)),
            ("tropicália", ("World",)),
            ("jùjú", ("World",)),
            ("grime", ("Hip Hop",)),
            ("trap metal", ("Hip Hop",)),
        ),
    )
    def test_each_reaches_what_it_was_ruled_to(
        self, stated: str, expected: tuple[str, ...]
    ) -> None:
        assert genres.chosen_in(stated) == expected

    def test_the_bare_dance_tag_is_the_dance_main(self) -> None:
        """873 library files carry it; ruled on 2026-10-01 that a name matched
        whatever its case means that name, so they move from Electronic."""
        assert genres.chosen_in("dance") == ("Dance",)
        assert genres.chosen_in("DANCE") == ("Dance",)

    def test_the_dance_main_written_by_a_tick_reads_back_as_itself(self) -> None:
        """No ruling stands between the name and its box."""
        assert genres.chosen_in(genres.stated_as(("Dance",))) == ("Dance",)
        assert genres.chosen_in(genres.stated_as(("Disco",))) == ("Dance", "Disco")

    @pytest.mark.parametrize(
        ("stored", "expected"),
        (
            ("Electronic; House", ("Electronic", "House")),
            ("Electronic; Deep House", ("Electronic", "House", "Deep House")),
            ("Electronic; Techno", ("Electronic", "Techno & Electro", "Techno")),
            ("Electronic; Disco", ("Dance", "Disco", "Electronic")),
        ),
    )
    def test_a_value_stored_before_the_split_reads_as_written(
        self, stored: str, expected: tuple[str, ...]
    ) -> None:
        """What a style's tick wrote while Electronic held every style. The
        stored Electronic stays and the style's new main is added; nothing is
        rewritten, so the album still answers an Electronic filter."""
        assert genres.chosen_in(stored) == expected

    @pytest.mark.parametrize(
        "stated", ("progressive rock", "new age", "spoken word", "neo soul")
    )
    def test_names_not_ruled_are_left_unrecognised(self, stated: str) -> None:
        """Rock kinds, soul, new age and spoken word were not ruled that day."""
        assert genres.chosen_in(stated) == ()

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
