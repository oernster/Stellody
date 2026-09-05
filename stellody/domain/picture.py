"""One decoded video frame, in the only terms every layer can hold.

A picture crosses the boundary as raw bytes and two lengths, the same way a
sleeve does: the domain may not know what a QImage is and infrastructure may
not decide how one is drawn. Three bytes a pixel, red then green then blue,
with no padding between rows, which is the one arrangement both the decoder and
the toolkit can state without either learning about the other.

Nothing here is a picture ABOUT a track. It is one moment of one, so it carries
no title, no path and no time: what moment it is belongs to whoever asked for
it; giving it a timestamp as well would be two answers to that question.
"""

from __future__ import annotations

from dataclasses import dataclass

BYTES_PER_PIXEL = 3


@dataclass(frozen=True, slots=True)
class Picture:
    """One frame, as rows of red, green and blue."""

    width: int
    height: int
    data: bytes

    def __post_init__(self) -> None:
        if self.width <= 0 or self.height <= 0:
            raise ValueError("a picture needs a positive width and height")
        if len(self.data) != self.expected_bytes:
            raise ValueError(
                f"a {self.width} by {self.height} picture needs "
                f"{self.expected_bytes} bytes, not {len(self.data)}"
            )

    @property
    def expected_bytes(self) -> int:
        """How many bytes a picture of this size holds."""
        return self.width * self.height * BYTES_PER_PIXEL

    @property
    def bytes_per_row(self) -> int:
        """The stride, which a toolkit needs to read the rows apart."""
        return self.width * BYTES_PER_PIXEL
