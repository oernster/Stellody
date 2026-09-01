"""Every menu entry either acts where it stands or says it cannot.

The rule the application already holds for its buttons, read across the menu
bar: a control that cannot do its job says so before it is pressed rather than
answering back once it has been. Expand all in the sleeves view was one breach
of it. Rescan with no music folder chosen was the other: it looked live on a
first run, then replied "Choose a music folder to begin" when pressed.

So this is a SWEEP rather than a test of one entry. The table below names every
entry in the bar along with where it is offered; the enumeration is checked
against the bar itself. An entry added later with nobody having decided when it
can act fails here, which is the point: the two defects above were both entries
that nobody had thought about in the second view.

Three situations, which is every combination the enabling actually turns on:
no music folder chosen, a folder chosen in the list, a folder chosen in the
sleeves. What sorting or playing is going on changes nothing here.
"""

from __future__ import annotations

import pytest
from conftest import RecordingPlayer
from PySide6.QtWidgets import QApplication
from tray_support import RememberingStore, build

from stellody.ui.settings_keys import SETTING_ROOT

# A folder that is never read. Nothing here scans; what is under test is the
# window's answer to having been pointed somewhere at all.
CHOSEN_ROOT = r"C:\music"

NOTHING_CHOSEN = "nothing chosen"
LIST_VIEW = "list"
SLEEVES_VIEW = "sleeves"
SITUATIONS = (NOTHING_CHOSEN, LIST_VIEW, SLEEVES_VIEW)

# Where each entry is offered. Read as one row per entry, one column per
# situation above, in that order.
EXPECTED = {
    "Choose music folder...": (True, True, True),
    # Nothing to scan until somewhere has been named.
    "Rescan": (False, True, True),
    # Nothing to forget: a window that has not been told to stop asking is
    # already asking, which is what this entry would restore.
    "Ask again when I close": (False, False, False),
    "Quit": (True, True, True),
    "Light appearance": (True, True, True),
    "Dark appearance": (True, True, True),
    # The grid is the tree's own model, so sorting reaches both views.
    "Sort Z to A": (True, True, True),
    # A sleeve holds nothing, so there is nothing there to open or shut.
    "Expand all": (True, True, False),
    "Collapse all": (True, True, False),
    "Equalizer...": (True, True, True),
    "Library health...": (True, True, True),
    "Model licence (GPL-3.0)": (True, True, True),
    "UI licence (LGPL-3.0)": (True, True, True),
    "About Stellody": (True, True, True),
    "Check for updates": (True, True, True),
}


def _entries(window) -> dict[str, bool]:
    """Every entry in the bar with the state it is in, keyed by its label.

    Each menu is told it is about to show first, because two entries work out
    what they can do at that moment rather than keeping it up to date. Reading
    them without that would report yesterday's answer.
    """
    found: dict[str, bool] = {}
    for top in window.menuBar().actions():
        menu = top.menu()
        if menu is None:
            continue
        menu.aboutToShow.emit()
        for action in menu.actions():
            if action.isSeparator():
                continue
            found[action.text().replace("&", "")] = action.isEnabled()
    return found


@pytest.fixture(params=SITUATIONS)
def situation(request, application: QApplication):
    """One window in each of the three situations, named by which it is in."""
    settings = {} if request.param == NOTHING_CHOSEN else {SETTING_ROOT: CHOSEN_ROOT}
    made = build(RememberingStore(settings), RecordingPlayer())
    if request.param == SLEEVES_VIEW:
        made.toggle_view()
        assert made.showing_covers
    yield request.param, made
    made.close()


def test_the_sweep_covers_every_entry_there_is(situation) -> None:
    """The table is the whole bar, so a new entry cannot slip past unclassified.

    This is the assertion that gives the rest of the file its value. Without
    it, an entry added to a menu tomorrow is simply not swept.
    """
    _, window = situation
    assert set(_entries(window)) == set(EXPECTED)


def test_every_entry_is_offered_only_where_it_can_act(situation) -> None:
    """The sweep proper: each entry against its row in the table."""
    name, window = situation
    column = SITUATIONS.index(name)
    expected = {label: row[column] for label, row in EXPECTED.items()}
    assert _entries(window) == expected
