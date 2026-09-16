"""The menu entries standing for picture buttons: what they act on, what they show.

The sweep beside this says when each entry is offered. This says the rest:
choosing one does what its button does; a tick read when its menu opens
says what is actually the case, however it came to be the case. Every state is
changed through the window rather than through the entry, since a tick that
only follows its own press is the defect this rule exists to rule out.
"""

from __future__ import annotations

import pytest
from PySide6.QtCore import QModelIndex
from PySide6.QtWidgets import QApplication, QMenu
from recording_player import RecordingPlayer
from tray_support import RememberingStore, build

from stellody.domain.playback import RepeatMode
from stellody.ui.covering import CoverSize
from stellody.ui.main_window import MainWindow
from stellody.ui.row_text import Column


@pytest.fixture
def window(application: QApplication) -> MainWindow:
    """A window with nothing remembered."""
    made = build(RememberingStore(), RecordingPlayer())
    yield made
    made.close()


def opened(window: MainWindow, title: str) -> QMenu:
    """The menu under one title, told it is about to show."""
    for top in window.menuBar().actions():
        if top.text() == title:
            top.menu().aboutToShow.emit()
            return top.menu()
    raise AssertionError(f"no {title} menu")


def test_the_edit_menu_sits_between_file_and_view(window: MainWindow) -> None:
    titles = [top.text() for top in window.menuBar().actions()]
    assert titles == ["&File", "&Edit", "&View", "&Sound", "&Control", "&Help"]


def test_mute_and_shuffle_are_ticked_as_the_transport_stands(
    window: MainWindow,
) -> None:
    for toggle, action, read in (
        (window.toggle_mute, window._mute_action, lambda: window._transport.muted),
        (
            window.toggle_shuffle,
            window._shuffle_action,
            lambda: window._transport.shuffled,
        ),
    ):
        for _ in range(2):
            toggle()
            opened(window, "&Sound")
            assert action.isChecked() is read()


def test_choosing_mute_from_the_menu_mutes(window: MainWindow) -> None:
    window._mute_action.trigger()
    assert window._transport.muted


def test_the_repeat_entry_ticked_is_the_mode_the_switch_is_holding(
    window: MainWindow,
) -> None:
    for _ in RepeatMode:
        window.toggle_repeat()
        opened(window, "&Sound")
        ticked = [
            mode for mode, one in window._repeat_actions.items() if one.isChecked()
        ]
        assert ticked == [window._transport.repeat]


def test_a_repeat_mode_is_chosen_by_name_without_stepping(
    window: MainWindow,
) -> None:
    window._repeat_actions[RepeatMode.ONE].trigger()
    assert window._transport.repeat is RepeatMode.ONE


def test_the_view_entries_follow_the_view_either_way(window: MainWindow) -> None:
    window._covers_action.trigger()
    assert window.showing_covers
    opened(window, "&View")
    assert window._covers_action.isChecked()
    window.toggle_view()
    opened(window, "&View")
    assert window._list_action.isChecked()
    assert not window._covers_action.isChecked()


def test_a_size_is_chosen_and_ticked(window: MainWindow) -> None:
    window.show_covers(True)
    window._size_actions[CoverSize.EXTRA_LARGE].trigger()
    assert window._cover_size is CoverSize.EXTRA_LARGE
    window.toggle_cover_size()
    opened(window, "&View")
    ticked = [size for size, one in window._size_actions.items() if one.isChecked()]
    assert ticked == [window._cover_size]


def test_search_is_ticked_while_the_box_is_open(window: MainWindow) -> None:
    window._search_action.trigger()
    assert window._tray.searching
    window.toggle_search()
    opened(window, "&Edit")
    assert not window._search_action.isChecked()


def test_play_starts_then_offers_to_pause(window: MainWindow) -> None:
    """Named for what a press would do, as the button's picture is."""
    window.toggle_view()
    first = window._model.index(0, Column.TITLE, QModelIndex())
    window._grid.setCurrentIndex(first)
    opened(window, "&Control")
    assert window._play_action.text() == "&Play"
    window._play_action.trigger()
    assert window._transport.playing
    opened(window, "&Control")
    assert window._play_action.text() == "&Pause"
    window._stop_action.trigger()
    assert not window._transport.state.is_active


def test_filter_is_ticked_while_its_button_is_held_down(window: MainWindow) -> None:
    window._tray.filter_button.setChecked(True)
    opened(window, "&Edit")
    assert window._filter_action.isChecked()


@pytest.mark.parametrize(
    "button, action, title",
    (
        (lambda w: w._bottom_tray.repair_button, lambda w: w._repair_action, "&File"),
        (lambda w: w._tray.discover_button, lambda w: w._discover_action, "&File"),
        (lambda w: w._tray.play_button, lambda w: w._play_action, "&Control"),
        (lambda w: w._tray.stop_button, lambda w: w._stop_action, "&Control"),
        (
            lambda w: w._tray.previous_button,
            lambda w: w._previous_action,
            "&Control",
        ),
        (lambda w: w._tray.next_button, lambda w: w._next_action, "&Control"),
    ),
)
def test_an_entry_is_offered_exactly_where_its_button_is(
    window: MainWindow, button, action, title: str
) -> None:
    """Planted both ways, so neither answer can come from the window as built."""
    for enabled in (True, False):
        button(window).setEnabled(enabled)
        opened(window, title)
        assert action(window).isEnabled() is enabled
