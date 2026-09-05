"""The search and the store the cover chooser is driven against.

Neither reaches anything. `ChooseCover` itself is real in every test here, so
what is stood in for is the pair of things underneath it: the archive, which
would otherwise open a connection, plus the artwork store, which would
otherwise write. Qt is never stood in for.
"""

from __future__ import annotations

import threading

from stellody.application.choosing_covers import Wanted, always_wanted
from stellody.domain.cover_choice import CoverCandidate, CoverOffer

FRONT = CoverCandidate(
    release="The Planets  1997  GB",
    image_url="https://example.invalid/front.jpg",
    thumbnail_url="https://example.invalid/front-250.jpg",
    largest_px=1200,
    is_front=True,
)
BACK = CoverCandidate(
    release="The Planets  1997  GB",
    image_url="https://example.invalid/back.jpg",
    thumbnail_url="https://example.invalid/back-250.jpg",
    largest_px=500,
)
KEPT = b"kept-bytes"


class FakeSearch:
    """An archive that answers from a script rather than from the network."""

    def __init__(
        self,
        candidates: tuple[CoverCandidate, ...] = (FRONT, BACK),
        pictures: dict[str, bytes] | None = None,
        gate: threading.Event | None = None,
        refused: bool = False,
    ) -> None:
        self.candidates = candidates
        self.refused = refused
        self.pictures = {} if pictures is None else pictures
        self.gate = gate
        self.searched: list[tuple[str, str]] = []
        self.fetched: list[str] = []
        self.asked: list[Wanted] = []

    def search(
        self, artist: str, album: str, wanted: Wanted = always_wanted
    ) -> CoverOffer:
        """Answer the script, holding at the gate when a test set one.

        The question is recorded rather than acted on, so a test can say what
        the real archive would have been asked between its slow parts.
        """
        self.searched.append((artist, album))
        self.asked.append(wanted)
        if self.gate is not None:
            self.gate.wait()
        return CoverOffer(self.candidates, refused=self.refused)

    def fetch(self, url: str, wanted: Wanted = always_wanted) -> bytes | None:
        """The bytes a test put at this address; None when it put none."""
        self.fetched.append(url)
        self.asked.append(wanted)
        return self.pictures.get(url)


class RaisingSearch:
    """An archive that fails the way a decoder or a socket layer would."""

    def search(
        self, artist: str, album: str, wanted: Wanted = always_wanted
    ) -> CoverOffer:
        """Raise, as a name that will not resolve does."""
        raise RuntimeError("the archive went away mid search")

    def fetch(self, url: str, wanted: Wanted = always_wanted) -> bytes | None:
        """Raise, for the same reason."""
        raise RuntimeError("the picture went away mid fetch")


class FakeArtwork:
    """An artwork store that keeps in memory rather than on disk."""

    def __init__(self, keeps: bool = True) -> None:
        self.keeps = keeps
        self.kept: dict[str, bytes] = {}

    def remembered(self, key: str) -> bytes | None:
        """Whatever was kept for this album."""
        return self.kept.get(key)

    def read(self, key, sidecars, audio) -> bytes | None:
        """Never asked for here."""
        return self.remembered(key)

    def keep_chosen(self, key: str, data: bytes) -> bytes | None:
        """Keep the chosen picture, unless this store was told it cannot."""
        if not self.keeps:
            return None
        self.kept[key] = KEPT
        return KEPT
