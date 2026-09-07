"""How long a run has left, worked out with no run and no clock.

Every figure here is handed in, which is the point of the module being pure:
the rules about pace and projection are checked against arithmetic rather than
against a stopwatch, so they can be checked at all.
"""

from __future__ import annotations

import pytest

from stellody.domain.estimating import (
    MINIMUM_SAMPLES,
    SECONDS_PER_MINUTE,
    looking_up_seconds_left,
    narrowing_seconds_left,
    pace,
    projected_candidates,
    rounded_minutes,
)

# A pace of two seconds an artist, which is close to what the gap the terms ask
# for actually produces. Named so the arithmetic below reads as arithmetic.
EACH_S = 2.0


class TestThePace:
    """What a finished unit turned out to cost, rather than what it should."""

    def test_the_pace_comes_from_what_happened(self) -> None:
        """FR-D36: measured, never taken from the configured gap.

        Four artists that took twelve seconds cost three seconds each, whatever
        the terms ask for. A run meeting refusals is slower than its gap and an
        estimate saying otherwise is confidently wrong.
        """
        assert pace(done=4, elapsed_s=12.0) == 3.0

    def test_one_sample_is_not_enough_to_estimate(self) -> None:
        """FR-D38: a pace over a single artist is wrong by a factor."""
        assert pace(done=1, elapsed_s=9.0) is None

    def test_the_threshold_is_the_stated_one(self) -> None:
        """Exactly the minimum is enough; one short of it is not."""
        assert pace(done=MINIMUM_SAMPLES, elapsed_s=4.0) == 2.0
        assert pace(done=MINIMUM_SAMPLES - 1, elapsed_s=4.0) is None

    def test_no_time_having_passed_is_not_a_pace(self) -> None:
        """A run that has taken no time at all has not been measured yet."""
        assert pace(done=4, elapsed_s=0.0) is None


class TestProjectingTheSecondStage:
    """How big the second stage will be, before it has begun."""

    def test_the_second_stage_is_projected_from_the_first(self) -> None:
        """FR-D37, with the acceptance criteria's own figures.

        Two of ten artists finished, having turned up twelve candidates between
        them, projects sixty candidates across the whole stage.
        """
        assert projected_candidates(seen=12, artists_done=2, artists_total=10) == 60

    def test_nothing_finished_projects_nothing(self) -> None:
        """A rate cannot be read off no artists at all."""
        assert projected_candidates(seen=0, artists_done=0, artists_total=10) == 0

    def test_a_projection_is_a_whole_number_of_candidates(self) -> None:
        """Candidates are asked about one at a time; there is no half of one."""
        assert projected_candidates(seen=5, artists_done=2, artists_total=3) == 8


class TestWhileLookingUp:
    """The estimate that covers both halves, given only the first."""

    def test_it_covers_the_artists_left_and_the_candidates_to_come(self) -> None:
        """FR-D37: naming only the first stage understates the wait by most.

        Two of ten artists at two seconds each leaves eight artists, so sixteen
        seconds. Twelve candidates seen projects sixty, each costing half an
        artist because it is one request rather than two, so sixty seconds.
        """
        left = looking_up_seconds_left(
            done=2, total=10, elapsed_s=2 * EACH_S, candidates_seen=12
        )
        assert left == pytest.approx(16.0 + 60.0)

    def test_a_run_that_has_met_no_candidates_estimates_only_itself(self) -> None:
        """Nothing found so far projects nothing to come."""
        left = looking_up_seconds_left(
            done=2, total=6, elapsed_s=2 * EACH_S, candidates_seen=0
        )
        assert left == pytest.approx(8.0)

    def test_too_little_has_happened_to_say(self) -> None:
        """FR-D38: the whole estimate waits on the pace being worth having."""
        assert (
            looking_up_seconds_left(
                done=1, total=10, elapsed_s=EACH_S, candidates_seen=6
            )
            is None
        )

    def test_a_stage_past_its_own_total_has_nothing_left_of_it(self) -> None:
        """Guarded rather than trusted: a negative count would read as time."""
        left = looking_up_seconds_left(
            done=12, total=10, elapsed_s=12 * EACH_S, candidates_seen=0
        )
        assert left == pytest.approx(0.0)


class TestWhileNarrowing:
    """The second stage, where the count is known rather than projected."""

    def test_what_is_left_is_counted_rather_than_projected(self) -> None:
        """Ten candidates asked of thirty, at two seconds each, leaves forty."""
        left = narrowing_seconds_left(done=10, total=30, elapsed_s=10 * EACH_S)
        assert left == pytest.approx(40.0)

    def test_too_little_has_happened_to_say(self) -> None:
        """FR-D38 again, since each stage is measured on its own."""
        assert narrowing_seconds_left(done=1, total=30, elapsed_s=EACH_S) is None

    def test_a_stage_past_its_own_total_has_nothing_left_of_it(self) -> None:
        """The same guard, since the same drift is possible here."""
        left = narrowing_seconds_left(done=31, total=30, elapsed_s=31 * EACH_S)
        assert left == pytest.approx(0.0)


class TestSayingIt:
    """The rounding FR-D35 asks for, kept where the rule lives."""

    @pytest.mark.parametrize(
        ("seconds", "minutes"),
        [
            (0.0, 0),
            (SECONDS_PER_MINUTE - 1, 1),
            (SECONDS_PER_MINUTE, 1),
            (SECONDS_PER_MINUTE * 4 + 20, 4),
            (SECONDS_PER_MINUTE * 4 + 40, 5),
        ],
    )
    def test_it_reads_to_the_nearest_minute(self, seconds: float, minutes: int) -> None:
        """Somebody waiting wants the minute, never the second."""
        assert rounded_minutes(seconds) == minutes
