"""The two bars in the tray that a discovery run reports to.

They exist because the second half of a run used to report nothing, so a bar
that had stopped moving was indistinguishable from a hang; they became two on
2026-09-07, because one bar carrying both halves in turn says how far through
the current half a run is and nothing whatever about the other.

What is asserted here: that each half has its own bar, that a finished half is
left full rather than wound back, that the time is written at the right hand
end of whichever bar is moving, that the time can never land on top of a stage
name and that neither bar becomes a control.

The bars draw their own writing rather than handing Qt one string, since two
pieces of text are wanted in two places. So what is read here is `writing()`,
which answers what would be drawn and where; reading pixels back off a widget
would measure the platform's font instead.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPixmap
from PySide6.QtWidgets import QWidget

from stellody.application.values import DiscoveryProgress, DiscoveryStage
from stellody.ui.discovery_progress import (
    RESTING,
    STACK_GAP_PX,
    DiscoveryBars,
    stacked_height,
)
from stellody.ui.tray_metrics import BUTTON_PX

# A colour nothing else on a bar is painted in, so a pixel wearing it can only
# have come from the writing these tests are about.
MARK = "#ff00ff"


def make_bars() -> tuple[DiscoveryBars, QWidget]:
    """The pair with nothing behind it; the holder keeps them alive.

    Polished before it is handed over, since polishing is when a stylesheet
    hands its properties to a widget. A test that set the writing colour first
    had it quietly replaced by the application stylesheet another suite left
    standing, which showed up as a paint test passing alone and failing in a
    full run.
    """
    holder = QWidget()
    bars = DiscoveryBars(holder, BUTTON_PX)
    bars.ensurePolished()
    for bar in bars.bars.values():
        bar.ensurePolished()
    return bars, holder


def looking(done: int = 1, total: int = 4, artist: str = "Muddy Waters"):
    """A report from the first half of a run."""
    return DiscoveryProgress(artist=artist, done=done, total=total)


def narrowing(done: int = 6, total: int = 31, artist: str = "Robert Cray"):
    """A report from the second half."""
    return DiscoveryProgress(
        artist=artist, done=done, total=total, stage=DiscoveryStage.NARROWING
    )


def painted(bar) -> QPixmap:
    """A bar as it actually draws itself, rather than as it plans to."""
    picture = QPixmap(bar.size())
    picture.fill(Qt.GlobalColor.transparent)
    bar.render(picture)
    return picture


def marks_in(picture: QPixmap, where, colour: str) -> int:
    """How many pixels of that colour were painted inside that rectangle."""
    image = picture.toImage()
    wanted = QColor(colour).rgb()
    return sum(
        image.pixel(x, y) == wanted
        for x in range(where.left(), where.right() + 1)
        for y in range(where.top(), where.bottom() + 1)
    )


def test_there_is_a_bar_for_each_half_of_a_run(application) -> None:
    """The change asked for: one bar said nothing about the other half."""
    bars, _holder = make_bars()
    assert bars.looking_up.label == "Looking up"
    assert bars.checking_styles.label == "Checking styles"
    assert bars.looking_up is not bars.checking_styles


def test_at_rest_each_bar_names_itself_and_the_slot_says_what_it_is_for(
    application,
) -> None:
    """Reserved rather than hidden, so the tray never moves under anybody."""
    bars, _holder = make_bars()
    assert bars.resting
    assert bars.looking_up.writing().wanted == "Looking up"
    assert bars.checking_styles.writing().wanted == "Checking styles"
    assert bars.toolTip() == RESTING
    assert bars.looking_up.value() == 0
    assert bars.checking_styles.value() == 0


def test_a_stage_that_has_not_begun_shows_no_percentage(application) -> None:
    """Nought per cent and not started look the same; they do not read alike."""
    bars, _holder = make_bars()
    bars.show_progress(looking(done=0, total=4))
    assert "%" not in bars.checking_styles.writing().wanted
    assert "%" in bars.looking_up.writing().wanted


def test_neither_bar_is_ever_a_stop_on_the_ring(application) -> None:
    """A report is not a control, so the keyboard steps over the lot."""
    bars, _holder = make_bars()
    assert bars.focusPolicy() == Qt.FocusPolicy.NoFocus
    for bar in bars.bars.values():
        assert bar.focusPolicy() == Qt.FocusPolicy.NoFocus


def test_the_pair_fills_the_slot_one_bar_used_to(application) -> None:
    """Two bars where one stood, rather than a tray grown taller for them."""
    bars, _holder = make_bars()
    each = stacked_height(BUTTON_PX)
    assert bars.height() == BUTTON_PX
    assert bars.looking_up.height() == each
    assert bars.checking_styles.height() == each
    assert each * 2 + STACK_GAP_PX <= BUTTON_PX


def test_it_reserves_its_place_whatever_it_is_saying(application) -> None:
    """The width cannot follow the text, else the tray moves as it reports."""
    bars, _holder = make_bars()
    resting = bars.width()
    bars.show_progress(looking(artist="Jools Holland & His Rhythm & Blues"))
    assert bars.width() == resting


def test_the_first_half_draws_on_the_first_bar(application) -> None:
    """Counted in work finished, which is what a bar is answering."""
    bars, _holder = make_bars()
    bars.show_progress(looking(done=1, total=4))
    assert bars.looking_up.value() == 25
    assert bars.checking_styles.value() == 0


def test_the_second_half_draws_on_the_second_bar(application) -> None:
    """The half that used to report nothing at all now has a bar of its own."""
    bars, _holder = make_bars()
    bars.show_progress(narrowing(done=6, total=31))
    assert bars.checking_styles.value() == 19
    assert "Checking styles" in bars.checking_styles.writing().wanted


def test_reaching_the_second_half_leaves_the_first_bar_full(application) -> None:
    """A stage that is done stays done rather than being wound back.

    The whole reason for two bars. The run never announces a stage ending, so
    a report from the second half is itself the news that the first finished.
    """
    bars, _holder = make_bars()
    bars.show_progress(looking(done=2, total=4))
    bars.show_progress(narrowing(done=0, total=31))
    assert bars.looking_up.value() == 100
    assert bars.checking_styles.value() == 0
    assert "Looking up 100%" == bars.looking_up.writing().wanted


def test_it_names_the_stage_rather_than_the_artist(application) -> None:
    """No strip of a toolbar holds "Jools Holland & His Rhythm & Blues
    Orchestra", so the name goes where there is room for it."""
    bars, _holder = make_bars()
    long_name = "Jools Holland & His Rhythm & Blues Orchestra"
    bars.show_progress(looking(done=3, total=4, artist=long_name))
    assert "Looking up" in bars.looking_up.writing().wanted
    assert long_name not in bars.looking_up.writing().wanted
    assert long_name in bars.looking_up.toolTip()
    assert "4 of 4" in bars.toolTip()


def test_an_ended_run_puts_both_bars_back_to_resting(application) -> None:
    """However a run ended, the space goes back to naming itself."""
    bars, _holder = make_bars()
    bars.show_progress(narrowing(done=6, total=31), "4m")
    bars.rest()
    assert bars.resting
    assert bars.toolTip() == RESTING
    assert bars.looking_up.value() == 0
    assert bars.checking_styles.value() == 0


def test_it_writes_how_long_is_left_at_the_right_hand_end_of_the_moving_bar(
    application,
) -> None:
    """The reported fault: the time was only at the foot of the window.

    The bars are at the top and the status bar at the bottom, so somebody
    watching a percentage never met the sentence. FR-D35.
    """
    bars, _holder = make_bars()
    bars.show_progress(looking(), "4m")
    drawn = bars.looking_up.writing()
    assert drawn.brief == "4m"
    assert drawn.brief_at.right() >= drawn.middle_at.right()
    assert bars.checking_styles.writing().brief == ""


def test_the_time_moves_to_the_second_bar_when_the_run_does(application) -> None:
    """It belongs to whichever half is moving, since that is where the eye is."""
    bars, _holder = make_bars()
    bars.show_progress(looking(), "9m")
    bars.show_progress(narrowing(), "4m")
    assert bars.checking_styles.writing().brief == "4m"
    assert bars.looking_up.writing().brief == ""


def test_the_time_and_the_stage_are_never_drawn_over_each_other(application) -> None:
    """The room for the time is taken out BEFORE the stage name is centred.

    Asserted over the longest of everything rather than a comfortable case: a
    strip 170 pixels wide with the widest stage name, a full percentage and a
    run of hours is exactly where hoping for room would fail; it would fail in
    whatever font the machine happens to have rather than in this one.
    """
    bars, _holder = make_bars()
    bars.show_progress(narrowing(done=30, total=31), "180m")
    drawn = bars.checking_styles.writing()
    assert not drawn.collides
    assert drawn.middle_at.right() < drawn.brief_at.left()


def test_a_stage_name_with_no_room_left_is_shortened_rather_than_clipped(
    application,
) -> None:
    """What will not fit says so with an ellipsis rather than losing its end."""
    bars, _holder = make_bars()
    bars.show_progress(narrowing(done=30, total=31), "1000000m")
    drawn = bars.checking_styles.writing()
    assert not drawn.collides
    assert drawn.shortened
    assert len(drawn.middle) < len(drawn.wanted)


def test_a_run_with_no_pace_yet_writes_no_time_at_all(application) -> None:
    """A bar cannot say "under way" in three characters, so it says nothing."""
    bars, _holder = make_bars()
    bars.show_progress(looking())
    assert bars.looking_up.writing().brief == ""
    assert not bars.looking_up.writing().collides


def test_the_time_is_actually_drawn_on_the_bar(application) -> None:
    """The layout above says where it would go; this says it went there.

    A rectangle worked out correctly and then never painted would pass every
    other test in this file. Comparing two whole pictures does not catch it
    either; that was measured rather than assumed. Planting the removal of the
    drawing left such a test green, because reserving the room moves the stage
    name whether or not anything is then written in the room.

    So the writing is looked for where it belongs, in the colour it is written
    in, which is why the colour is set to one nothing else on the bar uses.
    """
    bars, _holder = make_bars()
    bars.looking_up.setProperty("writingColour", MARK)
    bars.show_progress(looking(), "4m")
    bar = bars.looking_up
    assert marks_in(painted(bar), bar.writing().brief_at, MARK) > 0


def test_nothing_is_written_at_the_end_when_there_is_no_time_to_give(
    application,
) -> None:
    """The unwanted sibling: a bar with no pace writes nothing over there."""
    bars, _holder = make_bars()
    bars.looking_up.setProperty("writingColour", MARK)
    bars.show_progress(looking())
    bar = bars.looking_up
    assert marks_in(painted(bar), bar.writing().brief_at, MARK) == 0


def test_the_writing_colour_comes_from_the_stylesheet(application) -> None:
    """The palette stays the one home for a colour value, painting included."""
    bars, _holder = make_bars()
    bars.looking_up.setProperty("writingColour", "#ffffff")
    assert bars.looking_up.writingColour == "#ffffff"
