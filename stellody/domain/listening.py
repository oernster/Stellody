"""What a listener leaves behind: a rating and a count of complete plays.

Both belong to a TRACK rather than to a file; both have to survive a
rescan, which rebuilds every album and every track afresh. So neither can be
attached to an object. The handle is the album's identity with the disc and
track number under it, which is what artwork already does and for the same
reason: a folder rename is not a different album.

Neither ever reaches the music. They are Stellody's own state and are kept
where Stellody's own state lives, which is the invariant the whole project
exists for.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, replace

from stellody.domain.identity import AlbumIdentity

# Zero is not a rating. It is the absence of one, which is how a rating is
# taken back once given.
NO_STARS = 0
MAXIMUM_STARS = 5
HANDLE_LENGTH = 16


@dataclass(frozen=True, slots=True)
class Listening:
    """One track's rating and how many times it has played out."""

    stars: int = NO_STARS
    plays: int = 0

    def __post_init__(self) -> None:
        if not NO_STARS <= self.stars <= MAXIMUM_STARS:
            raise ValueError(f"a rating runs from {NO_STARS} to {MAXIMUM_STARS}")
        if self.plays < 0:
            raise ValueError("a play count cannot be negative")

    @property
    def is_rated(self) -> bool:
        """True once somebody has said something about this track."""
        return self.stars > NO_STARS

    @property
    def is_empty(self) -> bool:
        """True while there is nothing here worth keeping."""
        return self.stars == NO_STARS and self.plays == 0

    def rated(self, stars: int) -> Listening:
        """This track at a new rating, the count untouched."""
        return replace(self, stars=stars)

    def played(self) -> Listening:
        """This track having played out once more.

        Once more rather than once, since a track played out twice is worth
        twice as much to anyone reading the number later.
        """
        return replace(self, plays=self.plays + 1)


def track_handle(album: AlbumIdentity, disc_number: int, track_number: int) -> str:
    """A stable handle for one track's own record.

    Built from the album's comparison key rather than from its display text,
    so a tag tidied up in a tagger does not orphan a rating; built from the
    numbers rather than from the title, so a title corrected in the same way
    does not either. The digest is here so the store holds one short column
    rather than four, exactly as the artwork cache does.
    """
    material = " ".join(album.key + (str(disc_number), str(track_number)))
    return hashlib.sha256(material.encode("utf-8")).hexdigest()[:HANDLE_LENGTH]
