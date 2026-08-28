"""Albums and the discs inside them."""

from __future__ import annotations

from dataclasses import dataclass

from stellody.domain.identity import AlbumIdentity
from stellody.domain.track import Track

FIRST_DISC = 1


@dataclass(frozen=True, slots=True)
class Disc:
    """One disc of an album, holding its tracks in order."""

    number: int
    tracks: tuple[Track, ...]

    def __post_init__(self) -> None:
        if self.number < FIRST_DISC:
            raise ValueError("disc numbers start at 1")

    @property
    def duration_ms(self) -> int:
        """Total playing time of this disc."""
        return sum(track.duration_ms for track in self.tracks)


@dataclass(frozen=True, slots=True)
class Album:
    """A complete album, however its tracks are laid out on disk."""

    identity: AlbumIdentity
    tracks: tuple[Track, ...]
    genre: str = ""

    def __post_init__(self) -> None:
        if not self.tracks:
            raise ValueError("an album needs at least one track")

    @property
    def discs(self) -> tuple[Disc, ...]:
        """The album's tracks grouped by disc, both levels in order."""
        numbers = sorted({track.disc_number for track in self.tracks})
        return tuple(
            Disc(
                number=number,
                tracks=tuple(
                    sorted(
                        (t for t in self.tracks if t.disc_number == number),
                        key=lambda t: t.ordering_key,
                    )
                ),
            )
            for number in numbers
        )

    @property
    def disc_count(self) -> int:
        """How many discs this album spans."""
        return len(self.discs)

    @property
    def track_count(self) -> int:
        """How many tracks the album holds across every disc."""
        return len(self.tracks)

    @property
    def duration_ms(self) -> int:
        """Total playing time of the whole album."""
        return sum(track.duration_ms for track in self.tracks)

    @property
    def artists(self) -> tuple[str, ...]:
        """Every artist appearing on the album, first appearance order."""
        seen: dict[str, None] = {}
        for disc in self.discs:
            for track in disc.tracks:
                for artist in track.artists:
                    seen.setdefault(artist, None)
        return tuple(seen)

    @property
    def is_high_resolution(self) -> bool:
        """True when any track exceeds CD rate or depth."""
        return any(track.is_high_resolution for track in self.tracks)

    @property
    def is_single_file(self) -> bool:
        """True when every track is a slice of one shared audio file."""
        paths = {track.source.path for track in self.tracks}
        return len(paths) == 1 and any(t.source.is_slice for t in self.tracks)

    def ordered_tracks(self) -> tuple[Track, ...]:
        """Every track in playing order, disc by disc."""
        return tuple(track for disc in self.discs for track in disc.tracks)
