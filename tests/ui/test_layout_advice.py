"""Telling somebody how a library wants laying out, before they lay one out.

Two guards worth having. The words live in ONE place, so the note and the
guide cannot come to say different things about the same rule. And the note is
offered to somebody who has never chosen a folder while staying out of the way
of somebody changing one, since advice nobody can dismiss for good stops being
advice and becomes an obstacle.
"""

from __future__ import annotations

import pytest
from conftest import RecordingPlayer
from PySide6.QtWidgets import QApplication, QFileDialog

# The window's own store fake, taken from where it already lives rather
# than copied: a second one would drift from the first.
from test_launch import FakeStore

from stellody.application.loading import LoadLibrary
from stellody.application.scan import ScanLibrary
from stellody.application.transport import Transport
from stellody.ui.guide import GuideDialog, guide_html
from stellody.ui.layout_advice import (
    HEADING,
    NOTE_HTML,
    LayoutAdviceDialog,
    layout_html,
)
from stellody.ui.main_window import MainWindow
from stellody.ui.settings_keys import SETTING_ROOT


def test_the_guide_carries_the_layout_advice_rather_than_a_copy() -> None:
    """One home for the words: the guide shows exactly what the module says."""
    assert layout_html() in guide_html()


def test_the_advice_names_the_trap_it_exists_to_warn_about() -> None:
    """A rip naming nothing joins another naming nothing. That is the point."""
    words = layout_html()
    assert "Unknown Artist" in words
    assert "Unknown Title" in words


def test_the_note_is_shorter_than_the_guide_it_points_at() -> None:
    """A wall of text where somebody wants to pick a folder is not read."""
    assert len(NOTE_HTML) < len(layout_html())


@pytest.fixture
def note(application: QApplication) -> LayoutAdviceDialog:
    """The note, built the way the folder picker builds it."""
    return LayoutAdviceDialog()


def test_the_note_starts_wanting_nothing(note: LayoutAdviceDialog) -> None:
    assert note.wants_guide is False


def test_carrying_on_asks_for_no_guide(note: LayoutAdviceDialog) -> None:
    note.choose_button.click()
    assert note.wants_guide is False


def test_asking_for_the_guide_says_so_and_still_carries_on(
    note: LayoutAdviceDialog,
) -> None:
    """Both buttons go on to the folder picker; only one asks for the guide."""
    note.guide_button.click()
    assert note.wants_guide is True
    assert note.isVisible() is False


def test_the_note_is_titled_the_way_the_guide_section_is(
    note: LayoutAdviceDialog,
) -> None:
    assert note.windowTitle() == HEADING


def _window(application: QApplication, root: str) -> MainWindow:
    """A window whose store holds this library root; none where it is empty."""
    store = FakeStore((), {SETTING_ROOT: root} if root else {})

    def session():
        return ScanLibrary(None, None, None, store), store

    return MainWindow(
        scan_session=session,
        loader=LoadLibrary(store),
        transport=Transport(RecordingPlayer()),
        settings=store,
    )


def _watch_the_picker(monkeypatch) -> list[str]:
    """Stand the folder picker down; record that it was reached."""
    reached: list[str] = []

    def picked(parent, title, start):
        reached.append(start)
        return ""

    monkeypatch.setattr(QFileDialog, "getExistingDirectory", picked)
    return reached


def _watch_the_note(monkeypatch) -> list[int]:
    """Stand the note down; record every time it would have opened."""
    opened: list[int] = []

    def shown(self):
        opened.append(1)
        return 0

    monkeypatch.setattr(LayoutAdviceDialog, "exec", shown)
    return opened


def test_somebody_who_has_never_chosen_is_told_how_a_library_is_laid_out(
    application: QApplication, monkeypatch
) -> None:
    opened = _watch_the_note(monkeypatch)
    _watch_the_picker(monkeypatch)
    made = _window(application, "")
    made.choose_folder()
    made.close()
    assert opened == [1]


def test_somebody_changing_folders_is_not_told_again(
    application: QApplication, monkeypatch
) -> None:
    """Advice that cannot be got rid of stops being advice."""
    opened = _watch_the_note(monkeypatch)
    _watch_the_picker(monkeypatch)
    made = _window(application, "H:/FLACMusic")
    made.choose_folder()
    made.close()
    assert opened == []


def test_the_picker_still_opens_after_the_note(
    application: QApplication, monkeypatch
) -> None:
    """The note informs a choice; it never stands in the way of one."""
    _watch_the_note(monkeypatch)
    reached = _watch_the_picker(monkeypatch)
    made = _window(application, "")
    made.choose_folder()
    made.close()
    assert reached == [""]


def test_asking_for_the_guide_from_the_note_opens_it(
    application: QApplication, monkeypatch
) -> None:
    """The button is not decoration: it reaches the guide the note points at."""
    _watch_the_picker(monkeypatch)
    monkeypatch.setattr(
        LayoutAdviceDialog,
        "exec",
        lambda self: setattr(self, "wants_guide", True) or 0,
    )
    opened: list[int] = []
    monkeypatch.setattr(GuideDialog, "exec", lambda self: opened.append(1) or 0)

    made = _window(application, "")
    made.choose_folder()
    made.close()
    assert opened == [1]


def test_the_button_it_opens_on_is_the_one_enter_presses(
    application: QApplication, note: LayoutAdviceDialog
) -> None:
    """A ring round one control while the keyboard works another is a lie.

    Shown first: a dialog nobody has raised has no focus chain to walk, so
    the question cannot be asked of one that is still hidden.
    """
    note.show()
    application.processEvents()
    assert note.first_stop() is note.choose_button
    assert note.choose_button.isDefault() is True
