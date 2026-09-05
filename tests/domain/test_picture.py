"""One frame, in the terms every layer can hold it in."""

from __future__ import annotations

import pytest

from stellody.domain.picture import BYTES_PER_PIXEL, Picture

WIDTH = 4
HEIGHT = 3


def full_of(value: int, width: int = WIDTH, height: int = HEIGHT) -> bytes:
    """Enough bytes for a picture that size, every pixel the same."""
    return bytes([value]) * (width * height * BYTES_PER_PIXEL)


def test_a_picture_states_what_it_holds() -> None:
    picture = Picture(width=WIDTH, height=HEIGHT, data=full_of(0))
    assert picture.expected_bytes == WIDTH * HEIGHT * BYTES_PER_PIXEL
    assert picture.bytes_per_row == WIDTH * BYTES_PER_PIXEL


@pytest.mark.parametrize(
    ("width", "height"),
    [(0, HEIGHT), (WIDTH, 0), (-1, HEIGHT), (WIDTH, -1)],
)
def test_a_picture_needs_a_real_size(width: int, height: int) -> None:
    with pytest.raises(ValueError, match="positive width and height"):
        Picture(width=width, height=height, data=b"")


@pytest.mark.parametrize("spare", [-1, 1])
def test_the_bytes_must_match_the_size_claimed(spare: int) -> None:
    """A short buffer drawn as a picture is a crash rather than a wrong colour."""
    data = full_of(0)
    data = data[:spare] if spare < 0 else data + b"\x00"
    with pytest.raises(ValueError, match="needs"):
        Picture(width=WIDTH, height=HEIGHT, data=data)


def test_a_picture_cannot_be_changed_once_made() -> None:
    picture = Picture(width=WIDTH, height=HEIGHT, data=full_of(7))
    with pytest.raises(AttributeError):
        picture.width = WIDTH + 1
