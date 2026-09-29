"""Asking about series only what has not been answered already.

The series half of `remembering.py`, kept apart so that module stays clear of
the line cap. The rule is that module's, applied through its `recalled`: an
answer stands for a month and is written down the moment it arrives.
FR-D69, FR-D70.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

from stellody.application.choosing_covers import Wanted, always_wanted
from stellody.application.discovery_ports import SeriesSource
from stellody.application.remembering import (
    SERIES,
    SERIES_OF,
    TITLED,
    Asking,
    CatalogueMemory,
    Clock,
    NothingKept,
    Recollection,
    recalled,
)
from stellody.domain.discovery import ReleaseGroup
from stellody.domain.series import Series


@dataclass(frozen=True, slots=True)
class RememberingSeries:
    """A series source that asks only what it has not been told already."""

    source: SeriesSource
    kept: Recollection
    now: Clock = time.time
    keeper: CatalogueMemory = field(default_factory=NothingKept)

    def _asking(self, kind: str) -> Asking:
        """Where answers of this kind are recalled from and noted to."""
        return Asking(self.kept, self.keeper, self.now, kind)

    def series_of(self, title: str, wanted: Wanted = always_wanted) -> tuple[str, ...]:
        """Which series this title is in, from memory where it is known."""
        return recalled(
            self._asking(SERIES_OF),
            title,
            self.kept.series_of,
            lambda: self.source.series_of(title, wanted),
        )

    def series(self, identifier: str, wanted: Wanted = always_wanted) -> Series:
        """What one series holds, from memory where it is known."""
        return recalled(
            self._asking(SERIES),
            identifier,
            self.kept.series,
            lambda: self.source.series(identifier, wanted),
        )

    def titled(
        self, stem: str, wanted: Wanted = always_wanted
    ) -> tuple[ReleaseGroup, ...]:
        """What a search for this stem answers, from memory where it is known."""
        return recalled(
            self._asking(TITLED),
            stem,
            self.kept.titled,
            lambda: self.source.titled(stem, wanted),
        )
