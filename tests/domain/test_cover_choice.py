"""What a candidate cover is; the order the chooser shows them in."""

from __future__ import annotations

import pytest

from stellody.domain.cover_choice import (
    THUMBNAIL_SIZES,
    CoverCandidate,
    ordered,
)

FULL = "https://coverartarchive.org/release/abc/1.jpg"
SMALL = "https://coverartarchive.org/release/abc/1-250.jpg"


def candidate(**overrides: object) -> CoverCandidate:
    """One candidate, with the fields a given test cares about."""
    fields: dict[str, object] = {
        "release": "Ether Song  2003-11-17  GB",
        "image_url": FULL,
        "thumbnail_url": SMALL,
    }
    fields.update(overrides)
    return CoverCandidate(**fields)  # type: ignore[arg-type]


class TestWhatACandidateNeeds:
    def test_it_needs_a_picture_to_point_at(self) -> None:
        with pytest.raises(ValueError, match="picture to point at"):
            candidate(image_url="")

    def test_it_needs_something_to_show_in_the_chooser(self) -> None:
        with pytest.raises(ValueError, match="show in the chooser"):
            candidate(thumbnail_url="")

    def test_a_size_cannot_be_negative(self) -> None:
        with pytest.raises(ValueError, match="negative number of pixels"):
            candidate(largest_px=-1)

    def test_it_is_frozen(self) -> None:
        with pytest.raises(AttributeError):
            candidate().release = "something else"  # type: ignore[misc]


class TestWhatItSaysAboutItself:
    def test_a_known_size_is_written_beside_the_release(self) -> None:
        assert candidate(largest_px=1200).described.endswith("(1200 px)")

    def test_an_unknown_size_is_left_unsaid(self) -> None:
        """Written as zero it reads as a measurement that came out empty."""
        assert candidate(largest_px=0).described == "Ether Song  2003-11-17  GB"


class TestTheOrderTheyAreShownIn:
    def test_fronts_come_first(self) -> None:
        back = candidate(release="back", is_front=False)
        front = candidate(release="front", is_front=True)
        assert [one.release for one in ordered((back, front))] == ["front", "back"]

    def test_larger_comes_before_smaller(self) -> None:
        small = candidate(release="small", largest_px=250)
        big = candidate(release="big", largest_px=1200)
        assert [one.release for one in ordered((small, big))] == ["big", "small"]

    def test_a_front_beats_a_larger_one_that_is_not(self) -> None:
        """Almost nobody wants the back of the sleeve first, however good it is."""
        big_back = candidate(release="back", largest_px=1200, is_front=False)
        small_front = candidate(release="front", largest_px=250, is_front=True)
        assert ordered((big_back, small_front))[0].release == "front"

    def test_the_archives_own_order_survives_a_tie(self) -> None:
        """Sorting is stable; nothing here knows better than the archive."""
        first = candidate(release="first", largest_px=500, is_front=True)
        second = candidate(release="second", largest_px=500, is_front=True)
        assert [one.release for one in ordered((first, second))] == ["first", "second"]

    def test_nothing_offered_orders_to_nothing(self) -> None:
        assert ordered(()) == ()


def test_the_sizes_are_named_largest_first() -> None:
    """Both the ordering and the client's reading depend on that direction."""
    assert THUMBNAIL_SIZES == tuple(sorted(THUMBNAIL_SIZES, reverse=True))
