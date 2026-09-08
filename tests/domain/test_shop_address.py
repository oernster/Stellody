"""Turning a ticked album into a shop's own search address.

The arithmetic of stage two, measured against the shops as they actually
answered on 2026-09-07 rather than against how they ought to work.
"""

from __future__ import annotations

import pytest

from stellody.domain.shopping import (
    Shop,
    WantedAlbum,
    addresses_at,
    copied_text,
    encoded,
)

HOUNDS = WantedAlbum(artist="Kate Bush", title="Hounds of Love")
AMBER = WantedAlbum(artist="Autechre", title="Amber")
QOBUZ = Shop(
    name="Qobuz",
    template="https://www.qobuz.com/gb-en/search?q={artist}%20{album}",
)
# Boomkat's row, which deliberately names the artist alone: its search answered
# nothing for two terms and 85 results for one.
BOOMKAT = Shop(
    name="Boomkat",
    template="https://boomkat.com/products?q[keywords]={artist}&q[format]=Download",
)


class TestTheEncoding:
    def test_a_space_becomes_a_percent_escape_rather_than_a_plus(self) -> None:
        """HDtracks shows a literal plus; every other shop took %20."""
        assert encoded("Kate Bush") == "Kate%20Bush"

    def test_the_unreserved_characters_are_left_alone(self) -> None:
        """Encoding what needs no encoding makes an address nobody can read."""
        assert encoded("A-Z.a_z~09") == "A-Z.a_z~09"

    def test_what_would_break_an_address_is_escaped(self) -> None:
        """A title holding an ampersand would otherwise start a parameter."""
        assert encoded("Q&A/2?") == "Q%26A%2F2%3F"

    def test_an_accented_letter_becomes_its_bytes(self) -> None:
        """A percent escape names a byte, so one letter can be two of them."""
        assert encoded("Sigur Rós") == "Sigur%20R%C3%B3s"


class TestWhatAnAlbumNeeds:
    def test_an_album_with_no_artist_is_refused(self) -> None:
        """An address built from a title alone finds the wrong record."""
        with pytest.raises(ValueError):
            WantedAlbum(artist="  ", title="Amber")

    def test_an_album_with_no_title_is_refused(self) -> None:
        """The unwanted sibling: a search for an artist and nothing else."""
        with pytest.raises(ValueError):
            WantedAlbum(artist="Autechre", title="")


class TestWhatAShopNeeds:
    def test_a_shop_with_no_name_is_refused(self) -> None:
        """A row nobody can label is a button nobody can read."""
        with pytest.raises(ValueError):
            Shop(name=" ", template="https://x/?q={album}")

    def test_a_shop_with_no_address_is_refused(self) -> None:
        """The unwanted sibling of the name."""
        with pytest.raises(ValueError):
            Shop(name="Nowhere", template="")

    def test_an_address_naming_neither_placeholder_is_refused(self) -> None:
        """FR-S11: it would open the same page whatever was ticked."""
        with pytest.raises(ValueError):
            Shop(name="Homepage", template="https://example.com/")

    def test_naming_the_artist_alone_is_enough(self) -> None:
        """Boomkat's row, which is the reason both are not required."""
        assert BOOMKAT.names_a_placeholder

    def test_naming_the_album_alone_is_enough(self) -> None:
        """The other half of the same rule."""
        assert Shop(name="Titles", template="https://x/?q={album}").names_a_placeholder


class TestTheAddress:
    def test_both_placeholders_are_filled_and_encoded(self) -> None:
        """The acceptance criterion FR-S10 states, to the character."""
        assert QOBUZ.address_for(HOUNDS) == (
            "https://www.qobuz.com/gb-en/search?q=Kate%20Bush%20Hounds%20of%20Love"
        )

    def test_a_template_naming_one_placeholder_leaves_the_other_out(self) -> None:
        """Boomkat gets the artist and nothing else, which is what works."""
        assert BOOMKAT.address_for(AMBER) == (
            "https://boomkat.com/products?q[keywords]=Autechre&q[format]=Download"
        )

    def test_an_address_carries_nothing_but_the_album(self) -> None:
        """NFR-S-PRIV-001, asserted rather than intended.

        Everything in the address is either the shop's own template or the two
        values that came off the ticked row. Checked by putting the template
        back together from the pieces rather than by reading the string for
        things that should not be there, which would only find what the test
        author thought of.
        """
        address = QOBUZ.address_for(HOUNDS)
        rebuilt = QOBUZ.template.replace("{artist}", encoded(HOUNDS.artist)).replace(
            "{album}", encoded(HOUNDS.title)
        )
        assert address == rebuilt

    def test_one_address_an_album_in_the_order_they_were_ticked(self) -> None:
        """No shop searches for two albums at once, so each gets its own."""
        assert addresses_at(QOBUZ, (HOUNDS, AMBER)) == (
            QOBUZ.address_for(HOUNDS),
            QOBUZ.address_for(AMBER),
        )

    def test_nothing_ticked_is_nothing_to_open(self) -> None:
        """The empty case, which the dialog prevents and this still answers."""
        assert addresses_at(QOBUZ, ()) == ()


class TestTheCopiedText:
    def test_an_album_reads_as_the_artist_then_the_title(self) -> None:
        """What somebody pastes into a shop nobody has configured."""
        assert HOUNDS.as_text == "Kate Bush - Hounds of Love"

    def test_every_ticked_album_is_a_line_of_its_own(self) -> None:
        """A list pastes as a list rather than as one run-on line."""
        assert copied_text((HOUNDS, AMBER)) == (
            "Kate Bush - Hounds of Love\nAutechre - Amber"
        )

    def test_nothing_ticked_copies_nothing(self) -> None:
        """The empty case again, answered rather than left to chance."""
        assert copied_text(()) == ""
