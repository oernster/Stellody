"""The pictures a search offered for an album, in the order to show them.

Pure: nothing here fetches anything. A candidate is a description of a picture
somebody could choose, carrying the two addresses it lives at and what little
is known about how good it is.

**How good is not the same as how big.** Measured against the archive on
2026-08-30, a release's listing names the thumbnail sizes it can serve, 250,
500 and 1200; it never names the pixel size of the original. So the largest
thumbnail on offer is what a candidate can honestly say about itself, which is
still enough to tell a scan from a proper cover: a poor one is rarely served
at 1200.
"""

from __future__ import annotations

from dataclasses import dataclass

# The sizes the archive serves a thumbnail at, largest first. Stated here
# because the ordering below is about them and nothing else knows them.
THUMBNAIL_SIZES = (1200, 500, 250)


@dataclass(frozen=True, slots=True)
class CoverCandidate:
    """One picture a search offered for an album."""

    release: str
    image_url: str
    thumbnail_url: str
    largest_px: int = 0
    is_front: bool = False

    def __post_init__(self) -> None:
        if not self.image_url:
            raise ValueError("a candidate needs a picture to point at")
        if not self.thumbnail_url:
            raise ValueError("a candidate needs something to show in the chooser")
        if self.largest_px < 0:
            raise ValueError("a picture cannot be a negative number of pixels wide")

    @property
    def described(self) -> str:
        """What the chooser writes under this picture.

        The release it belongs to, then the largest size the archive will
        serve. A size of nothing is left unsaid rather than written as zero,
        which reads as a measurement that was taken and came out empty.
        """
        if not self.largest_px:
            return self.release
        return f"{self.release}  ({self.largest_px} px)"


@dataclass(frozen=True, slots=True)
class CoverOffer:
    """What a search came back with, plus whether it was answered at all.

    **An empty offer and a refused one are different things** and were once
    the same thing here. Measured on 2026-08-31, MusicBrainz refused 6 of 10
    asks spaced at the one a second its own terms request; two asks five
    seconds apart were refused while a third was answered. The Cover Art
    Archive answered 4 of 4 in the same minute, so a refusal is not a rate
    anybody exceeded; nor is it rare. Reporting one as "nothing came back for
    this album" tells a listener their album has no art anywhere, which is a
    claim the search never made and which they are right to disbelieve.
    """

    candidates: tuple[CoverCandidate, ...] = ()
    refused: bool = False

    @property
    def is_empty(self) -> bool:
        """True when there is nothing to show, refused or simply not found."""
        return not self.candidates


def ordered(candidates: tuple[CoverCandidate, ...]) -> tuple[CoverCandidate, ...]:
    """Fronts before the rest, larger before smaller, otherwise as they came.

    A back cover and a picture of the disc are worth offering, since a listener
    may want one; they are not worth offering FIRST, because almost nobody
    does. Sorting is stable, so the order the archive returned survives inside
    each of these groups: that order is the archive's own judgement and
    nothing here knows better than it.
    """
    return tuple(
        sorted(candidates, key=lambda one: (not one.is_front, -one.largest_px))
    )
