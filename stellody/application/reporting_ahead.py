"""What lies ahead of a stage, stamped onto each report it makes. FR-D84.

A bar's time is the whole run's (FR-D37), so each report has to carry what the
later stages will cost. The stages themselves do not know: the artist stage
cannot see the series to come, nor the series stage the candidates. The run
does, so it hands each stage this in place of the bare report and keeps it up
to date as the run learns more.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

from stellody.application.candidate_genres import ProgressReport
from stellody.application.values import DiscoveryProgress, DiscoveryStage


@dataclass(slots=True)
class Ahead:
    """A report that adds what is still to come. Mutable: one run in flight."""

    report: ProgressReport
    # The series the series stage will look up, counted as the run starts.
    series: int = 0
    # The candidates the styles stage will ask about, known once the artists
    # are done.
    candidates: int = 0

    def __call__(self, progress: DiscoveryProgress) -> None:
        """Pass the report on, carrying what lies beyond its stage."""
        if progress.stage is DiscoveryStage.LOOKING_UP:
            progress = replace(progress, series=self.series)
        elif progress.stage is DiscoveryStage.SERIES:
            progress = replace(progress, candidates=self.candidates)
        self.report(progress)
