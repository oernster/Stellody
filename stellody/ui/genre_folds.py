"""Which of the genre grid's categories were left open, kept between runs.

Every category starts folded, so a grid of 21 mains fits a laptop screen with
room to spare; the few somebody opens are the ones they keep coming back to.
So what was open is remembered, separately for each dialog holding the grid,
since a run's question and an album's description are different jobs that open
different categories. Ruled by Oliver on 2026-10-01.

Stored as the mains' names in one setting, written the way a genre value is,
so the store holds a line a person could read. A name that is no longer a main
is passed over on reading rather than trusted, which is what a catalogue
change leaves behind.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from stellody.application.ports import SettingsStore
from stellody.domain.genres import MAINS, SEPARATOR


@dataclass(frozen=True, slots=True)
class Folds:
    """One dialog's memory of its open categories."""

    settings: SettingsStore
    key: str

    def opened(self) -> frozenset[str]:
        """The mains left open last time; none when nothing was ever kept."""
        stored = self.settings.get_setting(self.key, "")
        return frozenset(name for name in stored.split(SEPARATOR) if name in MAINS)

    def keep(self, opened: Iterable[str]) -> None:
        """Remember these mains as open, in catalogue order."""
        wanted = set(opened)
        self.settings.set_setting(
            self.key, SEPARATOR.join(name for name in MAINS if name in wanted)
        )
