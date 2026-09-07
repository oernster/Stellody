"""The hand-written catalogues a discovery run is driven against.

Shared by the run tests and the narrowing tests, which were one module until
the pair of them went over the line cap. Everything here stands still and
answers from what it was handed, so what a test asserts is the order things
happen in rather than anything a network did.
"""

from __future__ import annotations

from stellody.application.discovering import RateRefused
from stellody.application.values import DiscoveryProgress
from stellody.domain.album import Album
from stellody.domain.discovery import ReleaseGroup, SimilarArtist
from stellody.domain.identity import AlbumIdentity
from stellody.domain.track import CD_SAMPLE_RATE, Track, TrackSource

ROCK = ("Rock",)


def make_album(artist: str, title: str, genre: str = "Rock") -> Album:
    """A held album, described by the three things discovery reads."""
    track = Track(
        source=TrackSource(path="a.flac"),
        disc_number=1,
        track_number=1,
        title="A Track",
        artists=(artist,),
        duration_ms=1000,
        sample_rate=CD_SAMPLE_RATE,
        bit_depth=16,
    )
    return Album(
        identity=AlbumIdentity(album_artist=artist, title=title),
        tracks=(track,),
        genre=genre,
    )


class Catalogue:
    """A catalogue that answers from what it was handed, counting the asks."""

    def __init__(
        self,
        identities: dict[str, tuple[str, ...]] | None = None,
        albums: dict[str, tuple[ReleaseGroup, ...]] | None = None,
        genres: dict[str, tuple[str, ...]] | None = None,
        raises: Exception | None = None,
        refusals: int = 0,
    ) -> None:
        self._identities = identities or {}
        self._albums = albums or {}
        self._genres = genres or {}
        self._raises = raises
        self._refusals = refusals
        self.identified: list[str] = []
        self.albums_asked: list[str] = []
        self.genres_asked: list[str] = []

    def identify(self, name: str) -> tuple[str, ...]:
        """Every artist this name reaches, as this fake was told."""
        self.identified.append(name)
        if self._refusals:
            self._refusals -= 1
            raise RateRefused("asked to wait")
        if self._raises is not None:
            raise self._raises
        return self._identities.get(name, (name.lower(),))

    def albums_of(self, identifier: str) -> tuple[ReleaseGroup, ...]:
        """Everything this artist released, as this fake was told."""
        self.albums_asked.append(identifier)
        return self._albums.get(identifier, ())

    def genres_of(self, identifier: str) -> tuple[str, ...]:
        """What this artist plays, as this fake was told."""
        self.genres_asked.append(identifier)
        return self._genres.get(identifier, ())


class Similarity:
    """A similarity catalogue answering with one fixed list."""

    def __init__(self, artists: tuple[SimilarArtist, ...] = ()) -> None:
        self._artists = artists
        self.asked: list[tuple[str, int]] = []

    def similar_to(self, identifier: str, wanted: int) -> tuple[SimilarArtist, ...]:
        """The artists this fake stands for; the ask is recorded."""
        self.asked.append((identifier, wanted))
        return self._artists


class Waits:
    """A pause that waits for nothing and remembers being asked to."""

    def __init__(self) -> None:
        self.waited: list[float] = []

    def __call__(self, seconds: float) -> None:
        """Record the wait rather than take it."""
        self.waited.append(seconds)


class Recorder:
    """A window that writes down every report it is handed."""

    def __init__(self) -> None:
        self.seen: list[DiscoveryProgress] = []

    def __call__(self, progress: DiscoveryProgress) -> None:
        """Keep the report rather than draw it."""
        self.seen.append(progress)


class Memory:
    """A genre memory over a dict, recording what it was asked to keep."""

    def __init__(self, known: dict[str, tuple[str, ...]] | None = None) -> None:
        self.known = known or {}
        self.kept: list[dict[str, tuple[str, ...]]] = []

    def remembered(self) -> dict[str, tuple[str, ...]]:
        """A copy, so a run cannot edit this fake's own answer under it."""
        return dict(self.known)

    def remember(self, known: dict[str, tuple[str, ...]]) -> None:
        """Record what the run learned."""
        self.kept.append(dict(known))


def never() -> bool:
    """A run nobody cancels."""
    return False


def nothing(progress: DiscoveryProgress) -> None:
    """A window nobody is watching."""
