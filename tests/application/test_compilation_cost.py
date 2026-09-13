"""FR-D52: what including compilations costs, stated before anything is asked.

Arithmetic over the library and the catalogue memory with the pace handed in,
so every case runs with no network and no clock.
"""

from __future__ import annotations

import pytest
from discovery_support import ROCK, make_album, make_compilation

from stellody.application.compilation_cost import CompilationCost, Pricing
from stellody.application.remembering import (
    IDENTIFIERS,
    MEMORY_LIFE_S,
    Recollection,
)
from stellody.domain.album import Album
from stellody.domain.estimating import REQUESTS_PER_SOURCE_ARTIST

# Any moment will do, so long as every case agrees on it.
NOW = 1_000_000_000.0
# The gap NFR-PERF-001 names, handed in the way the composition root hands it.
GAP_S = 1.1
# What a remembered answer holds; only whether one is held matters here.
KNOWN = ("an-identifier",)


class Kept:
    """A catalogue memory answering with one recollection, counting its reads."""

    def __init__(self, recollection: Recollection | None = None) -> None:
        self.recollection = recollection or Recollection()
        self.reads = 0

    def remembered(self) -> Recollection:
        """The recollection this fake was handed."""
        self.reads += 1
        return self.recollection

    def note(self, kind: str, key: str, answer: object, when: float) -> None:
        """Never asked here: pricing learns nothing."""

    def remember(self, kept: Recollection) -> None:
        """Never asked here: pricing learns nothing."""


def answered(*names: str, at: float = NOW) -> Recollection:
    """A memory holding an answer for each of these names, written at `at`."""
    return Recollection(
        identifiers={name: KNOWN for name in names},
        written_at={f"{IDENTIFIERS}:{name}": at for name in names},
    )


def priced(albums: tuple[Album, ...], memory: Kept) -> Pricing:
    """The pricing for this library over this memory, at the permitted pace."""
    cost = CompilationCost(recall=memory, request_gap_s=GAP_S, now=lambda: NOW)
    return cost.pricing(albums)


def test_only_names_not_yet_looked_up_are_counted() -> None:
    """A standing answer costs no request, so it costs no time either."""
    held = (make_compilation("Rock", "Dilby", "Tinlicker"),)
    assert priced(held, Kept(answered("Dilby"))).of(ROCK).names == 1


def test_an_answer_past_its_life_is_counted_again() -> None:
    """A run asks again once an answer is a month old, so the price does too."""
    stale = NOW - MEMORY_LIFE_S - 1
    held = (make_compilation("Rock", "Dilby", "Tinlicker"),)
    assert priced(held, Kept(answered("Dilby", at=stale))).of(ROCK).names == 2


def test_a_credit_a_run_would_ask_about_anyway_costs_nothing() -> None:
    """Only what ticking the box ADDS is its cost."""
    held = (
        make_album("Tinlicker", "This Is Not Our Universe"),
        make_compilation("Rock", "Tinlicker"),
    )
    assert priced(held, Kept()).of(ROCK).names == 0


def test_the_time_is_priced_at_the_permitted_pace() -> None:
    """Arithmetic rather than prediction: two paced requests a name."""
    credits = ("Dilby", "Tinlicker", "Andhim")
    cost = priced((make_compilation("Rock", *credits),), Kept()).of(ROCK)
    assert cost.names == len(credits)
    assert cost.seconds == pytest.approx(
        len(credits) * REQUESTS_PER_SOURCE_ARTIST * GAP_S
    )


def test_compilations_outside_the_ticks_cost_nothing() -> None:
    """Including compilations does not widen the genres, so neither does the price."""
    held = (make_compilation("Jazz", "Dilby"),)
    assert priced(held, Kept()).of(ROCK).names == 0


def test_the_memory_is_read_once_however_often_the_ticks_change() -> None:
    """The memory is megabytes on disk; a sweep moves 34 boxes."""
    memory = Kept()
    pricing = priced((make_compilation("Rock", "Dilby"),), memory)
    pricing.of(ROCK)
    pricing.of(("Jazz",))
    assert memory.reads == 1
