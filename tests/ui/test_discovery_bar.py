"""The bar in the tray that a discovery run reports to.

Its whole reason for existing is that the second half of a run used to report
nothing, so a bar that had stopped moving was indistinguishable from a hang.
What is asserted here: that it moves in both halves, that it says which half it
is in, that the time it now carries at its right end cannot land on top of that
and that it never becomes a control.

The bar draws its own writing rather than handing Qt one string, since two
pieces of text are wanted in two places. So what is read here is `writing()`,
which answers what would be drawn and where; reading pixels back off the widget
would measure the platform's font instead.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPixmap
from PySide6.QtWidgets import QWidget

from stellody.application.values import DiscoveryProgress, DiscoveryStage
from stellody.ui.discovery_progress import RESTING, DiscoveryBar
from stellody.ui.tray_metrics import BUTTON_PX

# A colour nothing else on the bar is painted in, so a pixel wearing it can
# only have come from the writing this file is about.
MARK = "#ff00ff"


def make_bar() -> tuple[DiscoveryBar, QWidget]:
    """A bar with nothing behind it; the holder is returned to keep it alive.

    Polished before it is handed over, since polishing is when a stylesheet
    hands its properties to a widget. A test that set the writing colour first
    had it quietly replaced by the application stylesheet another suite left
    standing, which showed up as a paint test passing alone and failing in a
    full run.
    """
    holder = QWidget()
    bar = DiscoveryBar(holder, BUTTON_PX)
    bar.ensurePolished()
    return bar, holder


def test_at_rest_it_says_what_the_space_is_for(application) -> None:
    """Reserved rather than hidden, so the tray never moves under anybody."""
    bar, _holder = make_bar()
    assert bar.writing().wanted == RESTING
    assert bar.value() == 0


def test_it_is_never_a_stop_on_the_ring(application) -> None:
    """A report is not a control, so the keyboard steps over it."""
    bar, _holder = make_bar()
    assert bar.focusPolicy() == Qt.FocusPolicy.NoFocus


def test_it_reserves_its_place_whatever_it_is_saying(application) -> None:
    """The width cannot follow the text, else the tray moves as it reports."""
    bar, _holder = make_bar()
    resting = bar.width()
    bar.show_progress(
        DiscoveryProgress(artist="Jools Holland & His Rhythm & Blues", done=1, total=4)
    )
    assert bar.width() == resting


def test_it_draws_how_far_through_the_stage_the_run_is(application) -> None:
    """Counted in work finished, which is what a bar is answering."""
    bar, _holder = make_bar()
    bar.show_progress(DiscoveryProgress(artist="Muddy Waters", done=1, total=4))
    assert bar.value() == 25


def test_it_names_the_stage_rather_than_the_artist(application) -> None:
    """No strip of a toolbar holds "Jools Holland & His Rhythm & Blues
    Orchestra", so the name goes where there is room for it."""
    bar, _holder = make_bar()
    long_name = "Jools Holland & His Rhythm & Blues Orchestra"
    bar.show_progress(DiscoveryProgress(artist=long_name, done=3, total=4))
    assert "Looking up" in bar.writing().wanted
    assert long_name not in bar.writing().wanted
    assert long_name in bar.toolTip()
    assert "4 of 4" in bar.toolTip()


def test_the_second_half_of_a_run_says_that_it_is_the_second_half(
    application,
) -> None:
    """The half that used to report nothing at all is named as its own."""
    bar, _holder = make_bar()
    bar.show_progress(
        DiscoveryProgress(
            artist="Robert Cray", done=6, total=31, stage=DiscoveryStage.NARROWING
        )
    )
    assert "Checking styles" in bar.writing().wanted
    assert "Robert Cray" in bar.toolTip()
    assert "7 of 31" in bar.toolTip()


def test_an_ended_run_puts_it_back_to_resting(application) -> None:
    """However a run ended, the space goes back to naming itself."""
    bar, _holder = make_bar()
    bar.show_progress(DiscoveryProgress(artist="Howlin' Wolf", done=2, total=4))
    bar.rest()
    assert bar.writing().wanted == RESTING
    assert bar.value() == 0


def test_it_writes_how_long_is_left_at_its_right_hand_end(application) -> None:
    """The reported fault: the time was only at the foot of the window.

    The bar is at the top and the status bar at the bottom, so somebody
    watching the percentage never met the sentence. FR-D35.
    """
    bar, _holder = make_bar()
    bar.show_progress(DiscoveryProgress(artist="Muddy Waters", done=1, total=4), "4m")
    drawn = bar.writing()
    assert drawn.brief == "4m"
    assert drawn.brief_at.right() >= drawn.middle_at.right()


def test_the_time_and_the_stage_are_never_drawn_over_each_other(application) -> None:
    """The room for the time is taken out BEFORE the stage name is centred.

    Asserted over the longest of everything rather than a comfortable case: a
    strip 170 pixels wide with the widest stage name, a full percentage and a
    run of hours is exactly where hoping for room would fail; it would fail in
    whatever font the machine happens to have rather than in this one.
    """
    bar, _holder = make_bar()
    bar.show_progress(
        DiscoveryProgress(
            artist="Robert Cray", done=30, total=31, stage=DiscoveryStage.NARROWING
        ),
        "180m",
    )
    drawn = bar.writing()
    assert not drawn.collides
    assert drawn.middle_at.right() < drawn.brief_at.left()


def test_a_stage_name_with_no_room_left_is_shortened_rather_than_clipped(
    application,
) -> None:
    """What will not fit says so with an ellipsis rather than losing its end."""
    bar, _holder = make_bar()
    bar.show_progress(
        DiscoveryProgress(
            artist="Robert Cray", done=30, total=31, stage=DiscoveryStage.NARROWING
        ),
        "1000000m",
    )
    drawn = bar.writing()
    assert not drawn.collides
    assert drawn.shortened
    assert len(drawn.middle) < len(drawn.wanted)


def test_a_run_with_no_pace_yet_writes_no_time_at_all(application) -> None:
    """A bar cannot say "under way" in three characters, so it says nothing."""
    bar, _holder = make_bar()
    bar.show_progress(DiscoveryProgress(artist="Muddy Waters", done=1, total=4))
    assert bar.writing().brief == ""
    assert not bar.writing().collides


def test_resting_takes_the_time_off_again(application) -> None:
    """A finished run leaves no minutes hanging in the toolbar."""
    bar, _holder = make_bar()
    bar.show_progress(DiscoveryProgress(artist="Muddy Waters", done=1, total=4), "4m")
    bar.rest()
    assert bar.writing().brief == ""
    assert bar.writing().wanted == RESTING


def test_the_writing_colour_comes_from_the_stylesheet(application) -> None:
    """The palette stays the one home for a colour value, painting included."""
    bar, _holder = make_bar()
    bar.setProperty("writingColour", "#eef3ff")
    assert bar.writingColour == "#eef3ff"


def painted(bar: DiscoveryBar) -> QPixmap:
    """The bar as it actually draws itself, rather than as it plans to."""
    picture = QPixmap(bar.size())
    picture.fill(Qt.GlobalColor.transparent)
    bar.render(picture)
    return picture


def right_hand_end(picture: QPixmap):
    """The third of the bar the time is written in."""
    third = picture.width() // 3
    return picture.copy(picture.width() - third, 0, third, picture.height())


def marks_in(picture: QPixmap, where, colour: str) -> int:
    """How many pixels of that colour were painted inside that rectangle."""
    image = picture.toImage()
    wanted = QColor(colour).rgb()
    return sum(
        image.pixel(x, y) == wanted
        for x in range(where.left(), where.right() + 1)
        for y in range(where.top(), where.bottom() + 1)
    )


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
    bar, _holder = make_bar()
    bar.setProperty("writingColour", MARK)
    running = DiscoveryProgress(artist="Muddy Waters", done=1, total=4)
    bar.show_progress(running, "4m")
    assert marks_in(painted(bar), bar.writing().brief_at, MARK) > 0


def test_nothing_is_written_at_the_end_when_there_is_no_time_to_give(
    application,
) -> None:
    """The unwanted sibling: a bar with no pace writes nothing over there."""
    bar, _holder = make_bar()
    bar.setProperty("writingColour", MARK)
    bar.show_progress(DiscoveryProgress(artist="Muddy Waters", done=1, total=4))
    drawn = bar.writing()
    assert marks_in(painted(bar), drawn.brief_at, MARK) == 0
