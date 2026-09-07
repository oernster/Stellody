"""How long a run has left, said in the status bar.

Driven against a clock the test moves by hand, so a run of tens of minutes is
checked in no time and the answers are arithmetic rather than timing.
"""

from __future__ import annotations

import pytest
from discovery_wiring_support import make_window

from stellody.application.values import DiscoveryProgress, DiscoveryStage
from stellody.ui.run_estimate import (
    BRIEFLY_UNDER_A_MINUTE,
    MINUTES_LEFT,
    NOT_LONG,
    NOTHING_BRIEF,
    ONE_MINUTE,
    UNDER_WAY,
    RunEstimate,
)

# Two seconds an artist, which is close to what the gap the terms require
# actually produces. Named so the arithmetic below reads as arithmetic.
EACH_S = 2.0
MINUTE_S = 60.0


class Ticking:
    """A clock the test winds forward by hand."""

    def __init__(self) -> None:
        self.at = 0.0

    def __call__(self) -> float:
        """Whatever the test has wound it to."""
        return self.at


def looking(done: int, total: int, candidates: int = 0) -> DiscoveryProgress:
    """A report from the first stage of a run."""
    return DiscoveryProgress(
        artist="Muddy Waters",
        done=done,
        total=total,
        stage=DiscoveryStage.LOOKING_UP,
        candidates=candidates,
    )


def narrowing(done: int, total: int) -> DiscoveryProgress:
    """A report from the second stage of a run."""
    return DiscoveryProgress(
        artist="Howlin' Wolf",
        done=done,
        total=total,
        stage=DiscoveryStage.NARROWING,
    )


class TestNamingTheTimeLeft:
    """FR-D35, in the words somebody waiting actually reads."""

    def test_the_status_bar_names_the_time_left(self) -> None:
        """Two of sixty artists at two seconds each leaves about two minutes."""
        clock = Ticking()
        estimate = RunEstimate(now=clock)
        estimate.about(looking(done=0, total=60))
        clock.at = 2 * EACH_S
        assert estimate.about(
            looking(done=2, total=60)
        ).sentence == MINUTES_LEFT.format(minutes=2)

    def test_under_a_minute_is_said_as_under_a_minute(self) -> None:
        """A number of seconds is no use to somebody deciding whether to wait."""
        clock = Ticking()
        estimate = RunEstimate(now=clock)
        estimate.about(looking(done=0, total=6))
        clock.at = 2 * EACH_S
        assert estimate.about(looking(done=2, total=6)).sentence == NOT_LONG

    def test_a_single_minute_reads_as_a_minute(self) -> None:
        """Never "1 minutes"."""
        clock = Ticking()
        estimate = RunEstimate(now=clock)
        estimate.about(looking(done=0, total=32))
        clock.at = 2 * EACH_S
        assert estimate.about(looking(done=2, total=32)).sentence == ONE_MINUTE


class TestWhenItWillNotSay:
    """FR-D38: an honest silence beats a number that swings."""

    def test_one_sample_is_not_enough_to_estimate(self) -> None:
        """A pace over one artist is wrong by a factor after a refusal."""
        clock = Ticking()
        estimate = RunEstimate(now=clock)
        estimate.about(looking(done=0, total=60))
        clock.at = EACH_S
        assert estimate.about(looking(done=1, total=60)).sentence == UNDER_WAY

    def test_a_stage_too_young_to_have_a_pace_says_nothing(self) -> None:
        """One finished candidate is one sample, here as anywhere else."""
        clock = Ticking()
        estimate = RunEstimate(now=clock)
        estimate.about(narrowing(done=0, total=30))
        clock.at = EACH_S
        assert estimate.about(narrowing(done=1, total=30)).sentence == UNDER_WAY

    def test_the_second_stage_is_measured_from_when_it_began(self) -> None:
        """Not from when the run did, which would price it by the first stage.

        A candidate costs one request where an artist costs two, so carrying
        the first stage's elapsed time across states a pace that is wrong by
        the whole length of that stage. Forty seconds of looking up followed by
        four seconds of narrowing is a two second pace, not a twenty two second
        one.
        """
        clock = Ticking()
        estimate = RunEstimate(now=clock)
        estimate.about(looking(done=0, total=4))
        clock.at = 20 * EACH_S
        estimate.about(looking(done=4, total=4))
        estimate.about(narrowing(done=0, total=62))
        clock.at = 20 * EACH_S + 2 * EACH_S
        assert estimate.about(
            narrowing(done=2, total=62)
        ).sentence == MINUTES_LEFT.format(minutes=2)


class TestWhatThePaceIsTakenFrom:
    """FR-D36 and FR-D37, read off the words rather than off the arithmetic."""

    def test_a_slow_run_is_reported_as_slower(self) -> None:
        """The pace is the run's own, so refusals lengthen the answer."""
        quick, slow = Ticking(), Ticking()
        first, second = RunEstimate(now=quick), RunEstimate(now=slow)
        first.about(looking(done=0, total=60))
        second.about(looking(done=0, total=60))
        quick.at, slow.at = 2 * EACH_S, 4 * EACH_S
        assert first.about(looking(done=2, total=60)).sentence == MINUTES_LEFT.format(
            minutes=2
        )
        assert second.about(looking(done=2, total=60)).sentence == MINUTES_LEFT.format(
            minutes=4
        )

    def test_the_candidates_seen_lengthen_the_answer(self) -> None:
        """FR-D37: the second stage is in the number before it has begun."""
        clock = Ticking()
        bare, met = RunEstimate(now=clock), RunEstimate(now=clock)
        bare.about(looking(done=0, total=60))
        met.about(looking(done=0, total=60, candidates=0))
        clock.at = 2 * EACH_S
        without = bare.about(looking(done=2, total=60))
        within = met.about(looking(done=2, total=60, candidates=10))
        assert without.sentence == MINUTES_LEFT.format(minutes=2)
        assert within.sentence == MINUTES_LEFT.format(
            minutes=7
        ), "the projection is in it"


class TestTheWindowSaysIt:
    """The wiring: a report reaches the status bar as well as the bar."""

    def test_a_report_puts_the_time_left_in_the_status_bar(self, application) -> None:
        """FR-D35, through the window rather than through the object alone."""
        clock = Ticking()
        window = make_window(application)
        window._discovery_estimate = RunEstimate(now=clock)
        window.discovery_progressed(looking(done=0, total=60))
        clock.at = 2 * EACH_S
        window.discovery_progressed(looking(done=2, total=60))
        assert window.statusBar().said[-1] == MINUTES_LEFT.format(minutes=2)

    def test_a_stopped_run_says_nothing_further(self, application) -> None:
        """The stop already said its piece; the run reports until it notices."""
        window = make_window(application)
        window._discovery_stopping = True
        window.discovery_progressed(looking(done=2, total=60))
        assert window.statusBar().said == [], "it said nothing at all"

    def test_a_new_run_is_measured_from_its_own_start(self, application) -> None:
        """Else the last run's clock prices this one and says nothing for ages."""
        clock = Ticking()
        window = make_window(application)
        window._discovery_estimate = RunEstimate(now=clock)
        window.discovery_progressed(looking(done=0, total=60))
        clock.at = MINUTE_S * 10
        window.begin_discovery(("Rock",))
        try:
            window.discovery_progressed(looking(done=0, total=60))
            clock.at = MINUTE_S * 10 + 2 * EACH_S
            window.discovery_progressed(looking(done=2, total=60))
            assert window.statusBar().said[-1] == MINUTES_LEFT.format(minutes=2)
        finally:
            window._discovery_runner.wait()


@pytest.mark.parametrize("total", [0, 1])
def test_a_stage_with_nothing_in_it_says_nothing(total: int) -> None:
    """Guarded rather than trusted, since a run can be told to ask about none."""
    clock = Ticking()
    estimate = RunEstimate(now=clock)
    estimate.about(looking(done=0, total=total))
    clock.at = EACH_S
    assert estimate.about(looking(done=0, total=total)).sentence == UNDER_WAY


class TestBothPlacesAgree:
    """One reading of the pace, so the two surfaces cannot contradict.

    Asked twice, the sentence and the word would be taken a moment apart and
    could land either side of a rounding: the foot of the window saying four
    minutes while the toolbar says five is worse than either alone.
    """

    def test_the_word_on_the_bar_carries_the_same_number_as_the_sentence(
        self,
    ) -> None:
        """The plant that proved this was missing: a brief taken from twice
        the seconds left the whole suite green."""
        clock = Ticking()
        estimate = RunEstimate(now=clock)
        estimate.about(looking(done=0, total=60))
        clock.at = 2 * EACH_S
        said = estimate.about(looking(done=2, total=60))
        assert said.sentence == MINUTES_LEFT.format(minutes=2)
        assert said.brief == "2m"

    def test_under_a_minute_is_short_in_both(self) -> None:
        """The other end of the same agreement."""
        clock = Ticking()
        estimate = RunEstimate(now=clock)
        estimate.about(looking(done=0, total=6))
        clock.at = 2 * EACH_S
        said = estimate.about(looking(done=2, total=6))
        assert said.sentence == NOT_LONG
        assert said.brief == BRIEFLY_UNDER_A_MINUTE

    def test_a_run_with_no_pace_yet_gives_the_bar_nothing_to_write(self) -> None:
        """A bar cannot say "under way" in three characters, so it says none."""
        clock = Ticking()
        estimate = RunEstimate(now=clock)
        estimate.about(looking(done=0, total=60))
        said = estimate.about(looking(done=1, total=60))
        assert said.sentence == UNDER_WAY
        assert said.brief == NOTHING_BRIEF
