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
from stellody.domain.credit_evidence import Evidence
from stellody.domain.discovery import ReleaseGroup, SimilarArtist
from stellody.domain.series import Series

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

# The questions a catalogue is asked, named once. They are the keys the
# recollection holds its answers under, the prefix each answer's stamp carries
# and the word a noted answer names itself by, so a file can put an answer back
# where it came from. Three places that must agree, hence one name each.
#
# Identities were filed as "identifiers" until 2026-09-27, when the rule for
# which catalogue name matches a tag stopped ignoring only case (FR-D08). The
# answers given under the old rule are wrong under the new one: "Hernan
# Cattaneo" was remembered as nobody. So they are filed under a new name and
# the old section is never read again, which costs the next run one identity
# question per artist rather than leaving the old answers standing for a month.
IDENTIFIERS = "identities"
ALBUMS = "albums"
SIMILAR = "similar"
CREDITED = "credited"
# The three series questions: which series a title is in, what a series holds
# and what a search for a stem answers. FR-D69, FR-D70.
SERIES_OF = "series-of"
SERIES = "series"
TITLED = "titled"
# Every kind a recollection holds, so a stamp for a kind no longer asked about
# can be told apart from one that is and left behind.
KINDS = (IDENTIFIERS, ALBUMS, SIMILAR, CREDITED, SERIES_OF, SERIES, TITLED)
# When an answer with no stamp reads as written: before anything was, so it
# is asked about again and gives way to any answer that says when it came.
UNSTAMPED = 0.0


def stamp_for(kind: str, key: str) -> str:
    """How the moment an answer was written is filed: by kind, then key."""
    return f"{kind}:{key}"


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
    # Who a catalogue credited on a held title, by `Evidence.question`.
    credited: dict[str, tuple[str, ...]] = field(default_factory=dict)
    series_of: dict[str, tuple[str, ...]] = field(default_factory=dict)
    series: dict[str, Series] = field(default_factory=dict)
    titled: dict[str, tuple[ReleaseGroup, ...]] = field(default_factory=dict)
    # When each answer was written down, by the question it answers, kept in
    # one place rather than beside each answer so the three shapes above stay
    # what they are. A question with no stamp is one written by a Stellody
    # that did not keep them, so it is asked again.
    written_at: dict[str, float] = field(default_factory=dict)

    def standing(self, question: str, now: float) -> bool:
        """Whether the answer to this question is still worth reusing."""
        return now - self.written_at.get(question, UNSTAMPED) < MEMORY_LIFE_S

    def holds(self, kind: str, key: str, held: dict, now: float) -> bool:
        """Whether this answer is both known and still young enough to use.

        One home for the rule, since two readers need it: a run deciding
        whether to ask; the price of a run deciding whether it will.
        """
        return key in held and self.standing(stamp_for(kind, key), now)


def merged(standing: Recollection, kept: Recollection) -> Recollection:
    """The two laid together, keeping the later answer to each question.

    What saving rests on once two users can hold copies of the memory at once:
    a new run started while a stopped one winds down (FR-D27), a candidate
    opened while a run goes on. Saving used to write one copy whole, so a copy
    taken before somebody else learned something put back the memory as it was
    then; measured on 2026-09-18, against the real file. A question only one of
    the two holds comes from that one. A tie goes to `kept`, the copy being
    saved. Neither argument is changed.
    """
    result = Recollection(
        identifiers=dict(standing.identifiers),
        albums=dict(standing.albums),
        similar=dict(standing.similar),
        credited=dict(standing.credited),
        series_of=dict(standing.series_of),
        series=dict(standing.series),
        titled=dict(standing.titled),
        written_at=dict(standing.written_at),
    )
    for kind, answers, into in (
        (IDENTIFIERS, kept.identifiers, result.identifiers),
        (ALBUMS, kept.albums, result.albums),
        (SIMILAR, kept.similar, result.similar),
        (CREDITED, kept.credited, result.credited),
        (SERIES_OF, kept.series_of, result.series_of),
        (SERIES, kept.series, result.series),
        (TITLED, kept.titled, result.titled),
    ):
        for key, answer in answers.items():
            stamp = stamp_for(kind, key)
            when = kept.written_at.get(stamp, UNSTAMPED)
            if key in into and when < result.written_at.get(stamp, UNSTAMPED):
                continue
            into[key] = answer
            if stamp in kept.written_at:
                result.written_at[stamp] = when
    return result


class CatalogueMemory(Protocol):
    """Keeps a recollection between one run and the next.

    Read once when a run starts and written whole once when it ends, since a
    run that rewrote the whole file after every answer would write the same
    file two hundred times. Each answer is ALSO noted on its own as it
    arrives, which is what makes the whole file's lateness affordable: see
    `note` below.
    """

    def remembered(self) -> Recollection:
        """What is already known; an empty recollection where nothing is."""
        ...

    def note(self, kind: str, key: str, answer: object, when: float) -> None:
        """Keep ONE answer now, before whatever learned it can be lost.

        `remember` is enough for a run that ends. A run that dies never
        reaches it; everything it paid for dies with it: reported by
        Oliver on 2026-09-09 after an overnight run of fifty minutes. So an
        answer is written down the moment it arrives as well.

        The kind is one of the three named at the top of this module, so
        whoever keeps this can put the answer back where it came from.
        Failing to keep it is not an error, for the reason `remember` is not:
        what it costs is requests.
        """
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

    def note(self, kind: str, key: str, answer: object, when: float) -> None:
        """Drop it, deliberately."""

    def remember(self, kept: Recollection) -> None:
        """Drop it, deliberately."""


@dataclass(frozen=True, slots=True)
class Asking:
    """Where one kind of answer is recalled from and noted to."""

    kept: Recollection
    keeper: CatalogueMemory
    now: Clock
    kind: str


def recalled[Answer](
    asking: Asking, key: str, held: dict, ask: Callable[[], Answer]
) -> Answer:
    """The remembered answer while it stands; else asked, then written down.

    In hand and on the disk in the same breath, so a run that dies between
    this answer and the next keeps this one. One home for the rule, since the
    catalogue and the series source both keep their answers this way.
    """
    if asking.kept.holds(asking.kind, key, held, asking.now()):
        return held[key]
    found = ask()
    when = asking.now()
    held[key] = found
    asking.kept.written_at[stamp_for(asking.kind, key)] = when
    asking.keeper.note(asking.kind, key, found, when)
    return found


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
    # Where each answer is noted as it arrives. The same memory the run hands
    # its recollection to at the end, rather than a second collaborator: one
    # thing keeps what is learned, whether it is keeping one answer or all of
    # them. A caller with nowhere to keep anything leaves it alone.
    keeper: CatalogueMemory = field(default_factory=NothingKept)

    def identify(self, name: str, wanted: Wanted = always_wanted) -> tuple[str, ...]:
        """Who this name means, from memory where it is already known."""
        return recalled(
            Asking(self.kept, self.keeper, self.now, IDENTIFIERS),
            name,
            self.kept.identifiers,
            lambda: self.catalogue.identify(name, wanted),
        )

    def credited(
        self, evidence: Evidence, wanted: Wanted = always_wanted
    ) -> tuple[str, ...]:
        """Who is credited on a held title, from memory where it is known."""
        return recalled(
            Asking(self.kept, self.keeper, self.now, CREDITED),
            evidence.question,
            self.kept.credited,
            lambda: self.catalogue.credited(evidence, wanted),
        )

    def albums_of(
        self, identifier: str, wanted: Wanted = always_wanted
    ) -> tuple[ReleaseGroup, ...]:
        """What this artist released, from memory where it is already known."""
        return recalled(
            Asking(self.kept, self.keeper, self.now, ALBUMS),
            identifier,
            self.kept.albums,
            lambda: self.catalogue.albums_of(identifier, wanted),
        )

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
    # Where each answer is noted as it arrives, exactly as above.
    keeper: CatalogueMemory = field(default_factory=NothingKept)

    def similar_to(
        self, identifier: str, most: int, wanted: Wanted = always_wanted
    ) -> tuple[SimilarArtist, ...]:
        """Who resembles this artist, from memory where it is already known."""
        return recalled(
            Asking(self.kept, self.keeper, self.now, SIMILAR),
            similar_key(identifier, most),
            self.kept.similar,
            lambda: self.similarity.similar_to(identifier, most, wanted),
        )
