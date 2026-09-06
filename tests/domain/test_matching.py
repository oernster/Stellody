"""What makes an album offered by a catalogue one the library already holds.

The worked cases come from the reference library rather than from imagination:
every title in the first two tests is one somebody actually owns.
"""

from __future__ import annotations

import pytest

from stellody.domain.matching import ReleaseKind, ReleaseMatch, matched

PRESSINGS = [
    ("Back In Black (Remastered)", "back in black"),
    ("Brothers In Arms (Remastered)", "brothers in arms"),
    ("Venom (Deluxe Edition)", "venom"),
    ("Higher Than Heaven (Deluxe)", "higher than heaven"),
    ("Ready for the Weekend (Bonus Track Version)", "ready for the weekend"),
    ("The Stone Roses (Remastered 2009)", "the stone roses"),
    ("Light of the Fearless (Special Edition)", "light of the fearless"),
    ("Yours Truly (Tenth Anniversary Edition)", "yours truly"),
    ("Emotional Technology (Special Collector's Edition)", "emotional technology"),
    ("Aphrodite (Deluxe Experience Edition)", "aphrodite"),
    ("Show Us Your Hits (International Version)", "show us your hits"),
    ("Ride On Time - EP", "ride on time"),
    ("Freeek! - Single", "freeek!"),
    ("Achtung Baby - Remastered", "achtung baby"),
    ("Kind of Blue (Super Deluxe Edition) (Remastered)", "kind of blue"),
]

LEFT_ALONE = [
    "L.I.F.E. (Love Is for Ever)",
    "The Death of Slim Shady (Coup de Grâce)",
    "Global Underground #45: Danny Tenaglia - Brooklyn",
    "Underworld: Evolution (Original Motion Picture Soundtrack)",
    "Magikal Journey (The Hits Collection 1998-2008)",
    "John Digweed - Live at Twilo",
    "Teenage Dream (Instrumentals)",
    "Something (Karaoke Version)",
    "Something (Single Version)",
    "Moon Safari",
]


@pytest.mark.parametrize(("title", "key"), PRESSINGS)
def test_a_pressing_reduces_to_the_album_it_presses(title: str, key: str) -> None:
    """Every one of these is a pressing of the album beside it."""
    assert matched(title).key == key


@pytest.mark.parametrize("title", LEFT_ALONE)
def test_a_recording_keeps_what_names_it(title: str) -> None:
    """A qualifier that names a recording or belongs to a title stays."""
    assert matched(title).key == title.casefold()


def test_the_year_is_not_part_of_the_key() -> None:
    """A remaster's tag carries its own year; the catalogue carries the first."""
    assert matched("Nevermind (2011 Remaster)").key == matched("Nevermind").key


def test_a_library_reads_its_kind_out_of_the_title() -> None:
    """Nothing states a kind to a library, so the title has to."""
    held = matched("Secret World (Live)")
    assert held.key == "secret world"
    assert held.kinds == (ReleaseKind.LIVE,)


def test_a_catalogue_states_its_kind_and_says_it_again_in_the_title() -> None:
    """The word in the title says nothing the stated type has not."""
    offered = matched("Secret World Live", (ReleaseKind.LIVE,))
    assert offered.key == "secret world"
    assert offered.kinds == (ReleaseKind.LIVE,)


def test_the_two_sides_meet() -> None:
    """The whole point: one record, reached from either direction."""
    assert matched("Secret World (Live)") == matched(
        "Secret World Live", (ReleaseKind.LIVE,)
    )


def test_a_live_record_is_not_the_studio_one() -> None:
    """Same key, different kinds, so neither ever stands in for the other."""
    assert matched("Secret World (Live)") != matched("Secret World")


def test_a_kind_stated_twice_is_held_once() -> None:
    """Stated and named in the title is one kind, not two."""
    assert matched("Blue Lines (Remixes)", (ReleaseKind.REMIX,)).kinds == (
        ReleaseKind.REMIX,
    )


def test_a_venue_is_part_of_the_title() -> None:
    """`Live in Berlin` names a record; only a bare kind names a kind."""
    berlin = matched("The Wall (Live in Berlin)")
    assert berlin.key == "the wall (live in berlin)"
    assert berlin.kinds == ()


def test_a_kind_the_catalogue_did_not_state_is_left_in_the_title() -> None:
    """A title word only comes off when the type behind it was stated."""
    assert matched("Foo Live", (ReleaseKind.REMIX,)).key == "foo live"


def test_a_record_actually_called_live_keeps_its_name() -> None:
    """Reducing a title to nothing leaves an album nothing can tell apart."""
    assert matched("Live", (ReleaseKind.LIVE,)).key == "live"


def test_a_title_that_is_only_a_qualifier_keeps_it() -> None:
    """There is nothing behind the brackets to reduce to."""
    assert matched("(Deluxe Edition)").key == "(deluxe edition)"
    assert matched("(Live)").key == "(live)"


def test_an_empty_qualifier_names_nothing() -> None:
    """A segment with no words in it is neither a pressing nor a kind."""
    assert matched("Foo ()").key == "foo ()"


def test_connectives_alone_are_not_a_qualifier() -> None:
    """A real edition word is still needed, so this is part of the title."""
    assert matched("Foo (The And)").key == "foo (the and)"


def test_a_year_alone_is_not_a_pressing() -> None:
    """A date range is part of a title; the Django Reinhardt case."""
    assert matched("The Quintessential (1934-1940)").key == (
        "the quintessential (1934-1940)"
    )


def test_an_album_needs_something_left_to_be_matched_on() -> None:
    """A key of nothing would match every album at once."""
    with pytest.raises(ValueError, match="matched on"):
        ReleaseMatch(key="")


def test_kinds_are_held_in_catalogue_order() -> None:
    """Two matches naming the same kinds compare equal however they arrived."""
    one = matched("Foo", (ReleaseKind.REMIX, ReleaseKind.LIVE))
    other = matched("Foo", (ReleaseKind.LIVE, ReleaseKind.REMIX))
    assert one == other
    assert one.kinds == (ReleaseKind.LIVE, ReleaseKind.REMIX)
