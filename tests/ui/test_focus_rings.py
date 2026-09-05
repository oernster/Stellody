"""Rings belong to controls; the ring follows reading order.

Two independent checks, because neither alone catches the defect class: the
stylesheet must not name a pane or an item view as a ring target; no pane may
appear in the toolkit's own focus chain.
"""

from __future__ import annotations

import re

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QPushButton, QTreeView
from ring_support import RING_WALK, build_ring_window, ring_rules

from stellody.ui.theme import Mode, stylesheet
from stellody.ui.volume import DEFAULT_PERCENT

# A Qt class selector matches every SUBCLASS, so naming one of these reaches
# every scroll area, list, table and label in the application.
CONTAINER_SELECTORS = (
    "*",
    "QWidget",
    "QFrame",
    "QAbstractScrollArea",
    "QScrollArea",
    "QGroupBox",
    "QStackedWidget",
    "QSplitter",
    "QTabWidget",
)
# An item view needs no ring at all: focusing one already paints its current
# row, so a rectangle round the whole view outlines everything and selects
# nothing, which is what a click below the last row used to do.
ITEM_VIEWS = ("QTreeView", "QListView", "QTableView", "QListWidget", "QTreeWidget")
# The one sanctioned zero-size stop: the neutral start the main window opens on.
NEUTRAL_START = "NeutralStart"
# The enabled stops on the top tray, ahead of the library: choose, filter,
# search, volume, mute, theme and help. The four transport buttons sit between
# search and volume and are disabled with nothing playing, so they are not
# stops at all. The search box is not one either while it is closed, since Qt
# skips a hidden stop; opening it adds an eighth. What the library is drawn as
# used to be counted here and now sits on the bottom strip instead.
TOP_TRAY_STOPS = 7


@pytest.fixture
def window(application: QApplication):
    """The real main window, built as both ring suites build it."""
    yield from build_ring_window(application)


@pytest.mark.parametrize("mode", tuple(Mode))
def test_no_pane_is_named_as_a_ring_target(mode: Mode) -> None:
    for selector, _block in ring_rules(stylesheet(mode)):
        for container in CONTAINER_SELECTORS:
            bare = re.search(rf"(^|[\s,]){re.escape(container)}[:\s,]", selector)
            assert not bare, f"{container} named as a ring target in {selector!r}"


@pytest.mark.parametrize("mode", tuple(Mode))
def test_an_item_view_wears_no_ring_in_any_state(mode: Mode) -> None:
    """Its current row is the indicator, so the view itself needs nothing."""
    for selector, _block in ring_rules(stylesheet(mode)):
        for view in ITEM_VIEWS:
            assert view not in selector, f"{view} given a ring in {selector!r}"


def test_no_pane_appears_in_the_windows_focus_chain(
    application: QApplication, window
) -> None:
    """Walk the toolkit's own chain, so the answer is what a real Tab reaches."""
    seen: set[int] = set()
    for _ in range(RING_WALK):
        window.focusNextChild()
        current = application.focusWidget()
        if current is None or id(current) in seen:
            break
        seen.add(id(current))
        if current.objectName() == NEUTRAL_START:
            continue
        assert current.focusPolicy() != 0
        assert not (
            type(current).__name__ == "QWidget"
            and current.objectName() != NEUTRAL_START
        ), "a plain container reached the focus chain"


def test_the_menu_bar_is_the_first_stop(application: QApplication, window) -> None:
    """Somebody reaching for the keyboard should find File before a button.

    Qt gives a menu bar NO focus at all by default, measured: it answers Alt
    and F10 and nothing else, so Tab used to land on the first tray button and
    the menus could not be reached by Tab from anywhere.
    """
    assert window.menuBar().focusPolicy() is Qt.FocusPolicy.TabFocus
    window.focusNextChild()
    assert application.focusWidget() is window.menuBar()
    first = next(action.text() for action in window.menuBar().actions())
    assert first == "&File"


def test_the_ring_follows_reading_order(application: QApplication, window) -> None:
    """The tray is drawn above the library, so Tab must reach it first."""
    order = []
    seen: set[int] = set()
    for _ in range(RING_WALK):
        window.focusNextChild()
        current = application.focusWidget()
        if current is None or id(current) in seen:
            break
        seen.add(id(current))
        order.append(current)
    buttons = [w for w in order if isinstance(w, QPushButton)]
    trees = [w for w in order if isinstance(w, QTreeView)]
    assert trees, "the library is a stop"
    # The disabled controls are not stops: the four transport buttons with
    # nothing playing, plus the repair control that is not built yet. The ring
    # must not stall on a dead one.
    tips = [button.toolTip() for button in buttons]
    # The size button is disabled over the list; Qt skips a disabled stop,
    # so it is deliberately absent from this order. What the library is drawn
    # as now sits on the bottom strip after the errands rather than in the tray
    # above, so the ring reaches it there.
    assert tips == [
        "Choose music folder",
        "Filter the library",
        "Search the library",
        f"Volume {DEFAULT_PERCENT}%",
        "Mute",
        "Switch to the light appearance",
        "Help",
        "Buy the author a drink (opens your browser)",
        "Rescan the library",
        "Switch to album art",
        "Shape what is heard",
        "Turn shuffle on",
        "Repeat mode",
    ]
    top = buttons[:TOP_TRAY_STOPS]
    bottom = buttons[TOP_TRAY_STOPS:]
    assert order.index(trees[0]) > order.index(top[-1]), "the tray comes first"
    assert order.index(trees[0]) < order.index(bottom[0]), "the strip comes after"
    assert order[-1] is bottom[-1], "the bottom strip is the last thing reached"
    # Each tray is its own row, so an x comparison across the two would be
    # comparing different rows. Each is read on its own, where left to right
    # is the reading order.
    for row, name in ((top, "top tray"), (bottom, "bottom strip")):
        centres = [w.mapTo(window, w.rect().center()).x() for w in row]
        assert centres == sorted(centres), f"the {name}'s stops run left to right"
