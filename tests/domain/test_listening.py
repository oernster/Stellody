"""A rating and a count of complete plays, plus what they are attached to.

The handle is the part worth testing hardest. A rating that does not survive
a rescan is worse than no rating at all, because it looks like it worked until
the day the library is scanned again.
"""

from __future__ import annotations

import pytest

from stellody.domain.identity import AlbumIdentity
from stellody.domain.listening import (
    MAXIMUM_STARS,
    NO_STARS,
    Listening,
    track_handle,
)

PLANETS = AlbumIdentity(album_artist="Gustav Holst", title="The Planets", date="1974")


class TestARecord:
    def test_a_fresh_one_says_nothing(self) -> None:
        record = Listening()
        assert record.stars == NO_STARS
        assert record.plays == 0
        assert not record.is_rated
        assert record.is_empty

    def test_rating_it_leaves_the_count_alone(self) -> None:
        record = Listening(plays=3).rated(MAXIMUM_STARS)
        assert record.stars == MAXIMUM_STARS
        assert record.plays == 3
        assert record.is_rated

    def test_playing_it_leaves_the_rating_alone(self) -> None:
        record = Listening(stars=4).played()
        assert record.stars == 4
        assert record.plays == 1

    def test_it_counts_up_rather_than_being_set(self) -> None:
        """A track played out twice is worth twice as much to a reader."""
        assert Listening().played().played().played().plays == 3

    def test_a_rating_can_be_taken_back(self) -> None:
        """Nought is the absence of a rating, so it needs no second emptiness."""
        record = Listening(stars=5, plays=2).rated(NO_STARS)
        assert not record.is_rated
        assert not record.is_empty, "the plays are still worth keeping"

    def test_it_cannot_be_changed_in_place(self) -> None:
        with pytest.raises(AttributeError):
            Listening().stars = 3

    @pytest.mark.parametrize("stars", [-1, MAXIMUM_STARS + 1])
    def test_a_rating_outside_the_scale_is_refused(self, stars: int) -> None:
        with pytest.raises(ValueError, match="rating runs from"):
            Listening(stars=stars)

    def test_a_negative_count_is_refused(self) -> None:
        with pytest.raises(ValueError, match="cannot be negative"):
            Listening(plays=-1)


class TestTheHandle:
    def test_the_same_track_gives_the_same_handle(self) -> None:
        assert track_handle(PLANETS, 1, 4) == track_handle(PLANETS, 1, 4)

    def test_a_different_track_number_gives_a_different_one(self) -> None:
        assert track_handle(PLANETS, 1, 4) != track_handle(PLANETS, 1, 5)

    def test_a_different_disc_gives_a_different_one(self) -> None:
        """A two-disc set has a track 1 on each of them."""
        assert track_handle(PLANETS, 1, 1) != track_handle(PLANETS, 2, 1)

    def test_a_different_album_gives_a_different_one(self) -> None:
        other = AlbumIdentity(album_artist="Zero 7", title="Simple Things")
        assert track_handle(PLANETS, 1, 1) != track_handle(other, 1, 1)

    def test_tidying_a_tag_does_not_orphan_a_rating(self) -> None:
        """It is built from the comparison key, which case and spacing do not
        change. A tagger run over an album must not lose what it holds."""
        tidied = AlbumIdentity(
            album_artist="  gustav   holst ", title="the planets", date="1974"
        )
        assert track_handle(tidied, 1, 4) == track_handle(PLANETS, 1, 4)

    def test_it_is_short_enough_to_be_one_column(self) -> None:
        assert len(track_handle(PLANETS, 1, 1)) == 16
