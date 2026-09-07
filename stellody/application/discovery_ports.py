"""What a discovery run asks of the world, plus what can go wrong asking.

Split out of `discovering.py` on 2026-09-07, when that module went over the
line cap. The seam is the ordinary one: what a run NEEDS from outside itself,
stated as interfaces, against the run itself, which is the decisions. A reader
after the order things happen in wants the other file; a reader writing a
catalogue client wants this one.

They are declared here rather than in `ports.py` for the reason that module's
own note gives: it sits four lines short of the danger band, so adding to it
would force an unrelated file to be decomposed by a change with nothing to do
with it.
"""

from __future__ import annotations

from typing import Protocol

from stellody.domain.discovery import ReleaseGroup, SimilarArtist


class DiscoveryError(RuntimeError):
    """Something went wrong reaching a catalogue."""


class SourceUnavailable(DiscoveryError):
    """Nothing could be reached at all, so no later question will fare better."""


class RateRefused(DiscoveryError):
    """The catalogue asked to be asked again later."""


class SourceFailed(DiscoveryError):
    """One question failed for a reason of its own."""


class RunCancelled(DiscoveryError):
    """Somebody stopped the run while it was waiting out a refusal.

    Raised rather than returned, because it happens inside a wait several
    calls below the loop that decides what a run ends as: every frame between
    here and there would otherwise have to carry a "give up" answer that means
    nothing to any of them.
    """


class CatalogueSource(Protocol):
    """Knows which artist a name means and what that artist released."""

    def identify(self, name: str) -> tuple[str, ...]:
        """Every artist this name reaches; empty where it reaches none.

        More than one is not an error here: it is the answer; the decision
        about what to do with it belongs above rather than inside a client.
        """
        ...

    def albums_of(self, identifier: str) -> tuple[ReleaseGroup, ...]:
        """Everything this artist released, with each album's stated genres."""
        ...

    def genres_of(self, identifier: str) -> tuple[str, ...]:
        """What this artist is said to play; empty where nothing is said."""
        ...


class SimilaritySource(Protocol):
    """Knows which artists resemble a given one."""

    def similar_to(self, identifier: str, wanted: int) -> tuple[SimilarArtist, ...]:
        """The artists most like this one, at most `wanted` of them."""
        ...


class GenreMemory(Protocol):
    """Keeps what earlier runs learned about candidate artists.

    What a candidate plays never changes between one run and the next, while
    asking costs a whole second each time at the rate the catalogue permits.
    A run that remembers nothing asks the same questions for ever.
    """

    def remembered(self) -> dict[str, tuple[str, ...]]:
        """What is already known; empty where nothing is."""
        ...

    def remember(self, known: dict[str, tuple[str, ...]]) -> None:
        """Keep this for the next run. Failing to keep it is not an error."""
        ...


class NothingRemembered:
    """A memory that forgets, for a run given nowhere to keep anything.

    The null object rather than an optional collaborator, so the run has one
    path through it instead of two.
    """

    def remembered(self) -> dict[str, tuple[str, ...]]:
        """Nothing was kept, because nothing is kept."""
        return {}

    def remember(self, known: dict[str, tuple[str, ...]]) -> None:
        """Drop it, deliberately."""
