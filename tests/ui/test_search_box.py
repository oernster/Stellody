"""The search box: closed until asked for, forgotten when closed.

The tray is pictures. The box is the one thing in it that is not, so it stays
out of the way until somebody wants it, then leaves nothing behind when it
goes: a box out of sight while still narrowing the library is a library that
looks as though it has lost albums.
"""

from __future__ import annotations

import pytest
from PySide6.QtWidgets import QApplication, QWidget

from stellody.ui.toolbar import LibraryTray


@pytest.fixture
def tray(application: QApplication):
    """A tray whose search callbacks record what they were told."""
    parent = QWidget()
    typed: list[str] = []
    presses: list[int] = []
    made = LibraryTray(
        parent,
        choose_folder=lambda: None,
        toggle_theme=lambda: None,
        show_guide=lambda: None,
        show_about=lambda: None,
        toggle_search=lambda: presses.append(1),
        search_changed=typed.append,
    )
    parent.show()
    application.processEvents()
    made.typed = typed
    made.presses = presses
    yield made
    parent.close()


class TestOpeningAndClosing:
    def test_the_box_is_closed_until_it_is_asked_for(self, tray) -> None:
        assert not tray.searching
        assert tray.search_box.isHidden()

    def test_opening_it_shows_it_and_takes_the_caret(self, tray) -> None:
        tray.set_searching(True)
        assert tray.searching
        assert tray.search_box.hasFocus()

    def test_closing_it_forgets_what_was_typed(self, tray) -> None:
        tray.set_searching(True)
        tray.search_box.setText("venus")
        tray.set_searching(False)
        assert not tray.searching
        assert tray.search_box.text() == ""

    def test_the_button_only_asks(self, tray) -> None:
        """The button reports the press; opening the box is the window's call."""
        tray.search_button.click()
        assert tray.presses == [1]


class TestTyping:
    def test_each_change_is_reported(self, tray) -> None:
        tray.set_searching(True)
        tray.search_box.setText("ven")
        tray.search_box.setText("venus")
        assert tray.typed == ["ven", "venus"]

    def test_closing_reports_the_empty_phrase(self, tray) -> None:
        """Clearing is a change like any other, so the library comes back."""
        tray.set_searching(True)
        tray.search_box.setText("venus")
        tray.typed.clear()
        tray.set_searching(False)
        assert tray.typed == [""]


class TestRing:
    def test_the_box_follows_its_button(self, tray) -> None:
        stops = tray.ring_stops()
        assert stops.index(tray.search_box) == stops.index(tray.search_button) + 1

    def test_search_follows_the_filter_beside_it(self, tray) -> None:
        """Filter came between search and the folder button it used to follow.

        Its place is settled: a filter is a question about the library, as
        choosing a folder is, while search is a button and a box that nothing
        may come between.
        """
        stops = tray.ring_stops()
        assert stops.index(tray.filter_button) == stops.index(tray.choose_button) + 1
        assert stops.index(tray.search_button) == stops.index(tray.filter_button) + 1
