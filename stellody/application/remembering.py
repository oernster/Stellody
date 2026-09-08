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

**What this deliberately does NOT do is expire.** A remembered answer stands
until something clears it. That is the whole point: an answer with a lifetime
is an answer that differs before and after the lifetime, which is the fault
being fixed. The cost is that a record released after an artist was first
asked about will not appear until the memory is cleared, which is a decision
for a control somebody presses rather than for a clock nobody sees.

Nothing here opens a connection or reads a clock. It stands between the run
and a catalogue, keeping what it is given in a `Recollection` that whoever
built it decides what to do with.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from stellody.application.choosing_covers import Wanted, always_wanted
from stellody.application.discovery_ports import (
    CatalogueSource,
    SimilaritySource,
)
from stellody.domain.discovery import ReleaseGroup, SimilarArtist


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

    def identify(self, name: str, wanted: Wanted = always_wanted) -> tuple[str, ...]:
        """Who this name means, from memory where it is already known."""
        if name in self.kept.identifiers:
            return self.kept.identifiers[name]
        found = self.catalogue.identify(name, wanted)
        self.kept.identifiers[name] = found
        return found

    def albums_of(
        self, identifier: str, wanted: Wanted = always_wanted
    ) -> tuple[ReleaseGroup, ...]:
        """What this artist released, from memory where it is already known."""
        if identifier in self.kept.albums:
            return self.kept.albums[identifier]
        found = self.catalogue.albums_of(identifier, wanted)
        self.kept.albums[identifier] = found
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

    def similar_to(
        self, identifier: str, most: int, wanted: Wanted = always_wanted
    ) -> tuple[SimilarArtist, ...]:
        """Who resembles this artist, from memory where it is already known."""
        question = similar_key(identifier, most)
        if question in self.kept.similar:
            return self.kept.similar[question]
        found = self.similarity.similar_to(identifier, most, wanted)
        self.kept.similar[question] = found
        return found
