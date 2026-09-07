"""The dialog that asks what the library is missing.

Nothing behind it: starting and stopping are handed in and recorded, so what is
tested is the surface rather than a run.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QCloseEvent, QKeyEvent

from stellody.application.values import DiscoveryProgress
from stellody.domain.genres import GENRES
from stellody.ui.discovery_dialog import (
    CANCEL_LABEL,
    CLOSE_LABEL,
    RESTING,
    TITLE,
    DiscoveryDialog,
)
from stellody.ui.theme import DIALOG_TITLE_FONT_PX, Mode, stylesheet


class Watched:
    """A start and a stop that do nothing except remember being asked."""

    def __init__(self) -> None:
        self.started: list[tuple[str, ...]] = []
        self.stopped = 0

    def start(self, genres: tuple[str, ...]) -> None:
        """Record what a run was asked to cover."""
        self.started.append(genres)

    def stop(self) -> None:
        """Record that stopping was asked for."""
        self.stopped += 1


def make_dialog(qtbot=None) -> tuple[DiscoveryDialog, Watched]:
    """A dialog wired to a start and stop that only remember."""
    watched = Watched()
    dialog = DiscoveryDialog(start=watched.start, stop=watched.stop)
    return dialog, watched


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


def test_the_ticks_are_what_a_run_is_given() -> None:
    """The scoping that keeps a run naming a subset somebody chose."""
    dialog, watched = make_dialog()
    dialog.grid.boxes[GENRES[0]].setChecked(True)
    dialog.find_button.click()
    assert watched.started == [dialog.chosen()]
    assert dialog.running


def test_a_second_run_cannot_start() -> None:
    """Two runs racing would double the rate and race to replace one file."""
    dialog, watched = make_dialog()
    dialog.grid.boxes[GENRES[0]].setChecked(True)
    dialog.find_button.click()
    dialog._find()
    assert len(watched.started) == 1
    assert not dialog.find_button.isEnabled()


def test_ticking_during_a_run_does_not_re_enable_the_action() -> None:
    """The guard has to survive somebody fiddling with the grid mid-run."""
    dialog, _ = make_dialog()
    dialog.grid.boxes[GENRES[0]].setChecked(True)
    dialog.find_button.click()
    dialog.grid.boxes[GENRES[1]].setChecked(True)
    assert not dialog.find_button.isEnabled()


def test_progress_names_the_artist() -> None:
    """Eleven minutes of unnamed bar is indistinguishable from a hang."""
    dialog, _ = make_dialog()
    dialog.progressed(DiscoveryProgress(artist="Talk Talk", done=2, total=9))
    assert "Talk Talk" in dialog.message.text()
    assert "3 of 9" in dialog.message.text()
    assert dialog.bar.maximum() == 9


def test_the_button_offers_to_stop_while_a_run_is_under_way() -> None:
    """While something is happening, leaving and stopping are the same wish."""
    dialog, _ = make_dialog()
    assert dialog.close_button.text() == CLOSE_LABEL
    dialog.grid.boxes[GENRES[0]].setChecked(True)
    dialog.find_button.click()
    assert dialog.close_button.text() == CANCEL_LABEL


def test_cancelling_asks_the_run_to_stop_and_keeps_the_dialog() -> None:
    """A dialog that closed would leave the run with nowhere to report."""
    dialog, watched = make_dialog()
    dialog.grid.boxes[GENRES[0]].setChecked(True)
    dialog.find_button.click()
    dialog.close_button.click()
    assert watched.stopped == 1
    assert dialog.running
    assert dialog.result() == 0


def test_escape_during_a_run_cancels_rather_than_closing() -> None:
    """Escape reaches reject, which is why the guard lives there."""
    dialog, watched = make_dialog()
    dialog.grid.boxes[GENRES[0]].setChecked(True)
    dialog.find_button.click()
    dialog.reject()
    assert watched.stopped == 1
    assert dialog.running


def test_escape_with_no_run_leaves_the_dialog() -> None:
    """The guard must not disable closing the dialog the ordinary way."""
    dialog, watched = make_dialog()
    dialog.reject()
    assert watched.stopped == 0
    assert dialog.isHidden()


def test_closing_the_window_mid_run_cancels_and_stays() -> None:
    """A close is a cancel expressed differently; it gets the same answer."""
    dialog, watched = make_dialog()
    dialog.grid.boxes[GENRES[0]].setChecked(True)
    dialog.find_button.click()
    event = QCloseEvent()
    dialog.closeEvent(event)
    assert watched.stopped == 1
    assert not event.isAccepted()


def test_closing_the_window_with_no_run_closes_it() -> None:
    """The guard is about a run, not about the window."""
    dialog, watched = make_dialog()
    event = QCloseEvent()
    dialog.closeEvent(event)
    assert watched.stopped == 0
    assert event.isAccepted()


def test_a_finished_run_says_so_and_offers_another() -> None:
    """However it ended, the dialog goes back to being askable."""
    dialog, _ = make_dialog()
    dialog.grid.boxes[GENRES[0]].setChecked(True)
    dialog.find_button.click()
    dialog.finished("Found 3 albums you do not hold.")
    assert not dialog.running
    assert dialog.message.text() == "Found 3 albums you do not hold."
    assert dialog.find_button.isEnabled()
    assert not dialog.bar.isVisible()
    assert dialog.close_button.text() == CLOSE_LABEL


def test_a_finished_run_with_the_ticks_cleared_cannot_be_repeated() -> None:
    """The action follows the ticks again the moment a run ends."""
    dialog, _ = make_dialog()
    dialog.grid.boxes[GENRES[0]].setChecked(True)
    dialog.find_button.click()
    dialog.grid.boxes[GENRES[0]].setChecked(False)
    dialog.finished("Nothing to report.")
    assert not dialog.find_button.isEnabled()


def test_it_rests_before_it_is_asked_anything() -> None:
    """A dialog says what to do with it rather than showing an empty label."""
    dialog, _ = make_dialog()
    assert dialog.message.text() == RESTING
    assert not dialog.bar.isVisible()


def test_pressing_find_with_nothing_ticked_does_nothing() -> None:
    """Reachable by keyboard even while the button is disabled, so guarded."""
    dialog, watched = make_dialog()
    dialog._find()
    assert watched.started == []
    assert not dialog.running


def test_the_key_that_closes_it_is_the_ordinary_one() -> None:
    """Nothing here changes what Escape means for a dialog at rest."""
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
