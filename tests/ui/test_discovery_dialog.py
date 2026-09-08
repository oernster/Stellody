"""The dialog that asks what the library is missing.

Nothing behind it: starting is handed in and recorded, so what is tested is the
surface rather than a run.

Since 2026-09-07 the dialog hands the ticks over and closes, so it knows
nothing about a run once one has started. What a run does while it is under way
is asserted where it now happens, in `test_discovery_wiring.py` for the window
and `test_discovery_bar.py` for the bar it reports to.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeyEvent

from stellody.domain.genres import GENRES
from stellody.ui.dialogs import CONTROL_ICON_PX
from stellody.ui.discovery_dialog import (
    CLEAR_LABEL,
    RESTING,
    SELECT_ALL_LABEL,
    TITLE,
    DiscoveryDialog,
)
from stellody.ui.theme import DIALOG_TITLE_FONT_PX, Mode, stylesheet


class Watched:
    """A start that does nothing except remember being asked."""

    def __init__(self) -> None:
        self.started: list[tuple[str, ...]] = []

    def start(self, genres: tuple[str, ...]) -> None:
        """Record what a run was asked to cover."""
        self.started.append(genres)


def make_dialog() -> tuple[DiscoveryDialog, Watched]:
    """A dialog wired to a start that only remembers."""
    watched = Watched()
    return DiscoveryDialog(start=watched.start), watched


def test_grid_matches_the_catalogue() -> None:
    """One catalogue behind two grids, so the two cannot disagree."""
    dialog, _ = make_dialog()
    assert set(dialog.grid.boxes) == set(GENRES)


def test_action_needs_a_genre() -> None:
    """A run over no genres has nobody to ask about."""
    dialog, _ = make_dialog()
    assert not dialog.find_button.isEnabled()
    dialog.grid.boxes[GENRES[0]].setChecked(True)
    assert dialog.find_button.isEnabled()


def test_the_sweep_ticks_every_genre_in_one_press() -> None:
    """Ticking 34 boxes by hand to ask about a whole library is a chore."""
    dialog, _ = make_dialog()
    dialog.select_button.click()
    assert set(dialog.chosen()) == set(GENRES)


def test_a_second_press_clears_them_again() -> None:
    """With everything ticked the only thing left to offer is clearing."""
    dialog, _ = make_dialog()
    dialog.select_button.click()
    dialog.select_button.click()
    assert dialog.chosen() == ()


def test_the_sweep_says_what_a_press_would_do() -> None:
    """The convention both trays already follow, applied to this control."""
    dialog, _ = make_dialog()
    assert dialog.select_button.text() == SELECT_ALL_LABEL
    dialog.select_button.click()
    assert dialog.select_button.text() == CLEAR_LABEL


def test_ticking_the_last_box_by_hand_moves_the_sweep_too() -> None:
    """Read off the boxes rather than remembered from the last press."""
    dialog, _ = make_dialog()
    for name in GENRES:
        dialog.grid.boxes[name].setChecked(True)
    assert dialog.select_button.text() == CLEAR_LABEL
    dialog.grid.boxes[GENRES[0]].setChecked(False)
    assert dialog.select_button.text() == SELECT_ALL_LABEL


def test_the_sweep_is_a_button_rather_than_a_tick_box() -> None:
    """Distinct from the genres, so it cannot read as one more of them."""
    dialog, _ = make_dialog()
    assert dialog.select_button not in dialog.grid.boxes.values()
    assert set(dialog.grid.boxes) == set(GENRES)


def test_sweeping_leaves_the_dialog_open() -> None:
    """Somebody who swept by accident has lost nothing."""
    dialog, watched = make_dialog()
    dialog.select_button.click()
    assert dialog.isVisible() is False or dialog.result() == 0
    assert watched.started == [], "a sweep asks for nothing"


def test_the_ticks_are_what_a_run_is_given() -> None:
    """The scoping that keeps a run naming a subset somebody chose."""
    dialog, watched = make_dialog()
    dialog.grid.boxes[GENRES[0]].setChecked(True)
    dialog.find_button.click()
    assert watched.started == [(GENRES[0],)]


def test_finding_closes_the_dialog() -> None:
    """It asks, then it leaves: a run takes minutes and this is in the way.

    Accepted rather than rejected, since pressing Find is the dialog getting
    what it was opened for.
    """
    dialog, _ = make_dialog()
    dialog.grid.boxes[GENRES[0]].setChecked(True)
    dialog.find_button.click()
    assert dialog.isHidden()
    assert dialog.result() == 1


def test_pressing_find_with_nothing_ticked_does_nothing() -> None:
    """Reachable by keyboard even while the button is disabled, so guarded."""
    dialog, watched = make_dialog()
    dialog._find()
    assert watched.started == []
    # A dialog never shown reads as hidden whatever it did, so what is asked
    # is whether it ACCEPTED: a refused press must not close it.
    assert dialog.result() == 0


def test_both_controls_wear_their_artwork_at_the_shared_size() -> None:
    """The same rule the results controls answer to, for the same reason.

    Find carries the picture the button that opens this dialog wears, so a
    press here is visibly the thing that button promised. Close carries the
    way out. Both are asserted at the shared size, since Qt draws an icon far
    too small to notice unless a button is told otherwise.
    """
    dialog, _ = make_dialog()
    for control in (dialog.find_button, dialog.close_button):
        assert control.iconSize().width() == CONTROL_ICON_PX, control.text()
        assert control.iconSize().height() == CONTROL_ICON_PX, control.text()
        assert not control.icon().isNull(), control.text()


def test_it_says_what_to_do_with_it_and_where_the_answer_goes() -> None:
    """It will not be on screen to report, so it says where the report is."""
    dialog, _ = make_dialog()
    assert dialog.message.text() == RESTING
    assert "toolbar" in RESTING


def test_the_key_that_closes_it_is_the_ordinary_one() -> None:
    """Nothing here changes what Escape means for a dialog."""
    dialog, _ = make_dialog()
    event = QKeyEvent(
        QKeyEvent.Type.KeyPress, Qt.Key.Key_Escape, Qt.KeyboardModifier.NoModifier
    )
    dialog.keyPressEvent(event)
    assert dialog.isHidden()


def test_it_says_what_it_is_across_the_top_of_itself() -> None:
    """A picture-only button opens this, so its face has to name it.

    The same words as the title bar, from the same constant, since a heading
    that drifts from the window title is two names for one dialog.
    """
    dialog, _ = make_dialog()
    assert dialog.title.text() == TITLE == dialog.windowTitle()
    assert dialog.title.alignment() & Qt.AlignmentFlag.AlignHCenter
    assert dialog.title.focusPolicy() == Qt.FocusPolicy.NoFocus


def test_the_heading_is_the_first_thing_in_the_dialog() -> None:
    """Above the ticking rather than beside it, which is what makes it read."""
    dialog, _ = make_dialog()
    outer = dialog.layout()
    assert outer.itemAt(0).widget() is dialog.title
    assert outer.indexOf(dialog.title) < outer.indexOf(dialog.grid)


def test_the_appearance_draws_the_heading_larger_than_the_words_under_it() -> None:
    """The size lives in the stylesheet, so it is measured through one.

    Asserted after polishing: a fresh widget still carries the fallback font,
    so reading the font before that reports the default and passes whatever
    the rule says.
    """
    dialog, _ = make_dialog()
    for mode in Mode:
        dialog.setStyleSheet(stylesheet(mode))
        dialog.title.ensurePolished()
        dialog.message.ensurePolished()
        assert dialog.title.font().pixelSize() == DIALOG_TITLE_FONT_PX
        assert dialog.title.font().bold()
        assert dialog.title.font().pixelSize() > dialog.message.font().pointSize()
