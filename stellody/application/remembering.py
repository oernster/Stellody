"""Asking a catalogue only what it has never already answered.

Reported by Oliver on 2026-09-08, in the strongest terms and repeatedly: two
runs over the same library gave different answers. Sometimes an artist was
there and sometimes it was not; sometimes an artist's records could be looked
up and sometimes they could not.

**The cause was that a run remembered nothing.** Every run asked MusicBrainz
about every artist again, so the answer was whatever the service felt like
that minute: measured on 2026-09-08, 27 requests in 65 seconds with 21 of them
refused, which is how a run of seven artists came back holding one. Retrying
harder helps and cannot fix it, because it still makes the answer a property
of the service's mood rather than of the library.

**So an answer is kept and never asked for twice.** What a catalogue said
about an artist is written down and read back on the next run; only an artist
nothing is known about is asked about at all. Two runs over the same library
then give the same answer; a refusal can no longer take away something
already known.

**An answer does age, over a month rather than over minutes.** Oliver's own
statement of what is wanted: the same run over the same library should differ
over days or weeks, because the catalogues themselves change; it should not
differ over five minutes, because they do not. So an answer stands for
`MEMORY_LIFE_DAYS` and is then asked about again, which is the only way a
record released since would ever be seen.

**A refresh that cannot be made keeps what it had.** An artist whose second
asking is refused is reported as a failure of that run; the answer already in
the discovery file is then carried over for it, so nothing is lost by trying.
That is `carrying_over.py` doing its job, which is why nothing here catches
anything.

Nothing here opens a connection or reads a clock. It stands between the run
and a catalogue, keeping what it is given in a `Recollection` that whoever
built it decides what to do with.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Protocol

from stellody.application.choosing_covers import Wanted, always_wanted
from stellody.application.discovery_ports import (
    CatalogueSource,
    SimilaritySource,
)
from stellody.domain.discovery import ReleaseGroup, SimilarArtist

# How long an answer stands before it is asked about again. A month rather
# than a day, since what a catalogue holds about an artist who released a
# record in 1969 does not change often; long enough that a run over a library
# asks nothing at all most of the time, short enough that a record released
# this year is found this year.
MEMORY_LIFE_DAYS = 30
SECONDS_A_DAY = 86400
MEMORY_LIFE_S = MEMORY_LIFE_DAYS * SECONDS_A_DAY

# Answers the seconds since the epoch. Injected rather than reached for, so a
# test can stand a month away from now without waiting one.
Clock = Callable[[], float]


@dataclass(slots=True)
class Recollection:
    """Everything the catalogues have already said, by what was asked.

    Mutable by intention, which is unusual here: it is filled as a run goes
    and written down once at the end, so a run that answers about two hundred
    artists writes one file rather than two hundred. The dataclasses inside it
    stay frozen.
    """

    identifiers: dict[str, tuple[str, ...]] = field(default_factory=dict)
    albums: dict[str, tuple[ReleaseGroup, ...]] = field(default_factory=dict)
    similar: dict[str, tuple[SimilarArtist, ...]] = field(default_factory=dict)
    # When each answer was written down, by the question it answers, kept in
    # one place rather than beside each answer so the three shapes above stay
    # what they are. A question with no stamp is one written by a Stellody
    # that did not keep them, so it is asked again.
    written_at: dict[str, float] = field(default_factory=dict)

    def standing(self, question: str, now: float) -> bool:
        """Whether the answer to this question is still worth reusing."""
        return now - self.written_at.get(question, 0.0) < MEMORY_LIFE_S


class CatalogueMemory(Protocol):
    """Keeps a recollection between one run and the next.

    Read once when a run starts and written once when it ends, which is the
    shape the genre memory beside it already has: a run that wrote after every
    answer would write the same file two hundred times.
    """

    def remembered(self) -> Recollection:
        """What is already known; an empty recollection where nothing is."""
        ...

    def remember(self, kept: Recollection) -> None:
        """Keep this for the next run. Failing to keep it is not an error."""
        ...


class NothingKept:
    """A memory that keeps nothing, for a run given nowhere to keep it.

    The null object rather than an optional collaborator, so a run has one
    path through it instead of two.
    """

    def remembered(self) -> Recollection:
        """Nothing was kept, because nothing is kept."""
        return Recollection()

    def remember(self, kept: Recollection) -> None:
        """Drop it, deliberately."""


def similar_key(identifier: str, most: int) -> str:
    """How a request for similar artists is remembered.

    The count is part of the question rather than a detail of it: asked for
    ten and answered with ten, this cannot then answer a request for fifty.
    """
    return f"{identifier}:{most}"


@dataclass(frozen=True, slots=True)
class RememberingCatalogue:
    """A catalogue that asks only what it has not been told already."""

    catalogue: CatalogueSource
    kept: Recollection
    now: Clock = time.time

    def _standing(self, kind: str, key: str, held: dict) -> bool:
        """Whether this answer is both known and still young enough to use."""
        return key in held and self.kept.standing(f"{kind}:{key}", self.now())

    def _kept(self, kind: str, key: str, held: dict, found: object) -> None:
        """Write an answer down, with when it was written."""
        held[key] = found
        self.kept.written_at[f"{kind}:{key}"] = self.now()

    def identify(self, name: str, wanted: Wanted = always_wanted) -> tuple[str, ...]:
        """Who this name means, from memory where it is already known."""
        if self._standing("identifiers", name, self.kept.identifiers):
            return self.kept.identifiers[name]
        found = self.catalogue.identify(name, wanted)
        self._kept("identifiers", name, self.kept.identifiers, found)
        return found

    def albums_of(
        self, identifier: str, wanted: Wanted = always_wanted
    ) -> tuple[ReleaseGroup, ...]:
        """What this artist released, from memory where it is already known."""
        if self._standing("albums", identifier, self.kept.albums):
            return self.kept.albums[identifier]
        found = self.catalogue.albums_of(identifier, wanted)
        self._kept("albums", identifier, self.kept.albums, found)
        return found

    def genres_of(
        self, identifier: str, wanted: Wanted = always_wanted
    ) -> tuple[str, ...]:
        """What this artist plays, asked straight through.

        The one question already remembered elsewhere: the genre memory has
        kept this since before any of the rest was; two memories holding the
        same answer are two answers to disagree.
        """
        return self.catalogue.genres_of(identifier, wanted)


@dataclass(frozen=True, slots=True)
class RememberingSimilarity:
    """A similarity source that asks only what it has not been told already."""

    similarity: SimilaritySource
    kept: Recollection
    now: Clock = time.time

    def similar_to(
        self, identifier: str, most: int, wanted: Wanted = always_wanted
    ) -> tuple[SimilarArtist, ...]:
        """Who resembles this artist, from memory where it is already known."""
        question = similar_key(identifier, most)
        stamp = f"similar:{question}"
        if question in self.kept.similar and self.kept.standing(stamp, self.now()):
            return self.kept.similar[question]
        found = self.similarity.similar_to(identifier, most, wanted)
        self.kept.similar[question] = found
        self.kept.written_at[stamp] = self.now()
        return found
