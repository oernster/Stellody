"""Which stated genres are believed: a single vote is a stray.

The counts are MusicBrainz's own for Nirvana and Snoop Dogg, measured on
2026-09-30 after a house filter showed both through their stray tags.
"""

from __future__ import annotations

from stellody.domain.genre_votes import FEWEST_VOTES, believed

NIRVANA = (
    ("grunge", 67),
    ("alternative rock", 30),
    ("electronic", 1),
    ("psytrance", 1),
)
SNOOP_DOGG = (("hip hop", 21), ("gangsta rap", 13), ("house", 1))


def test_a_single_vote_beside_real_ones_is_dropped() -> None:
    """Nirvana's alternative rock goes too since 2026-10-02: 30 is under half
    of grunge's 67 (see the leading share below)."""
    assert believed(NIRVANA) == ("grunge",)
    assert believed(SNOOP_DOGG) == ("hip hop", "gangsta rap")


def test_the_fewest_votes_still_count() -> None:
    assert believed((("techno", FEWEST_VOTES), ("pop", 1))) == ("techno",)


def test_an_artist_tagged_once_throughout_keeps_every_tag() -> None:
    """Dropping them all would leave a little-known artist unjudged."""
    assert believed((("techno", 1), ("house", 1))) == ("techno", "house")


def test_nothing_stated_is_nothing_believed() -> None:
    assert believed(()) == ()


# MusicBrainz's own counts for Lady Gaga, measured on 2026-10-02 after an
# Electronic filter showed her. The one-vote tags are left in on purpose.
LADY_GAGA = (
    ("pop", 24),
    ("dance-pop", 20),
    ("electropop", 17),
    ("pop rock", 9),
    ("synth-pop", 7),
    ("electronic", 6),
    ("dance", 4),
    ("edm", 1),
    ("electro house", 1),
)


def test_a_genre_under_half_the_leading_votes_is_dropped() -> None:
    """Ruled by Oliver on 2026-10-02: electronic at 6 of 24 does not
    describe her, while dance-pop and electropop do."""
    assert believed(LADY_GAGA) == ("pop", "dance-pop", "electropop")


def test_exactly_half_the_leading_votes_is_kept() -> None:
    assert believed((("house", 10), ("techno", 5), ("trance", 4))) == (
        "house",
        "techno",
    )


def test_the_leading_genre_is_kept_wherever_it_was_stated() -> None:
    """Kept in the order stated; the leader need not come first."""
    assert believed((("techno", 3), ("house", 12))) == ("house",)
