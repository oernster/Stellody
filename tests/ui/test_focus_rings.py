"""Rings belong to controls; the ring follows reading order.

Two independent checks, because neither alone catches the defect class: the
stylesheet must not name a pane or an item view as a ring target; no pane may
appear in the toolkit's own focus chain.
"""

from __future__ import annotations

import pathlib
import re
import tempfile

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QHBoxLayout,
    QPushButton,
    QTreeView,
    QWidget,
)

from stellody.composition import build_window
from stellody.domain.equalising import Equalisation
from stellody.infrastructure.store import SqliteLibraryStore
from stellody.ui.close_prompt import ClosePrompt
from stellody.ui.equaliser import EqualiserDialog
from stellody.ui.ringed_check import RingedCheckBox
from stellody.ui.stars import StarRating
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
# The enabled stops on the top tray, ahead of the library: choose, search, the
# view toggle, the equaliser, volume, mute, theme and help. The four transport
# buttons sit between the equaliser and volume and are disabled with nothing
# playing, so they are not stops at all. The search box is not one either while
# it is closed, since Qt skips a hidden stop; opening it adds a ninth.
TOP_TRAY_STOPS = 8
RING_RULE = re.compile(r"([^{}]*):(?:focus|hover)[^{}]*\{([^{}]*)\}")
COMMENT = re.compile(r"/\*.*?\*/", re.DOTALL)


@pytest.fixture
def window(application: QApplication):
    """The real main window over a throwaway store."""
    store = SqliteLibraryStore(str(pathlib.Path(tempfile.mkdtemp()) / "t.sqlite3"))
    made = build_window(store)
    made.show()
    application.processEvents()
    yield made
    made.close()
    store.close()


def ring_rules(sheet: str) -> list[tuple[str, str]]:
    """Every selector whose focus or hover block paints a visible border.

    Comments are stripped first: a comment explaining why a class gets NO rule
    names that class; scanning it would report the explanation as the fault.
    """
    found = []
    for selector, block in RING_RULE.findall(COMMENT.sub("", sheet)):
        if "border" in block or "outline" in block:
            found.append((selector.strip(), block))
    return found


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
    # so it is deliberately absent from this order.
    assert tips == [
        "Choose music folder",
        "Search the library",
        "Switch to album art",
        "Shape what is heard",
        f"Volume {DEFAULT_PERCENT}%",
        "Mute",
        "Switch to the light appearance",
        "Help",
        "Buy the author a drink (opens your browser)",
        "Rescan the library",
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


# A control that takes focus and paints nothing is the one defect the two
# checks above cannot see: they say which classes must NOT ring, while this
# says every class that CAN be landed on must. A checkbox shipped with no rule
# at all, so Tab stopped on it and nothing on screen reported that it had.
# Item views are the sanctioned exception and are listed as such rather than
# quietly passing: their current row is the indicator.
# Long enough for the walk to come back round to where it started.
RING_WALK = 40
# Stops the stylesheet is right not to name. A zero-size holder has nothing to
# paint a ring on. The other two paint their own and say in their modules why
# the sheet cannot do it for them: five glyphs standing for one value must ring
# once rather than five times; a checkbox's square belongs to Qt, which takes
# the whole subcontrol over the moment a sheet names it. Each is listed here
# rather than passing quietly, then each is proved below.
NOTHING_TO_PAINT = "_NeutralStart"
PAINTS_ITS_OWN_RING = ("StarRating", "RingedCheckBox")


def _qt_class(widget: QWidget) -> str:
    """The class a stylesheet selector would have to name to reach `widget`.

    A Qt class selector matches every subclass, so a view of our own is styled
    by the Qt class it derives from. Reporting the leaf name instead would ask
    for a rule per subclass, which is how this check first failed against the
    grid rather than against anything actually missing a ring.
    """
    for klass in type(widget).__mro__:
        if klass.__module__.startswith("PySide6"):
            return klass.__name__
    return type(widget).__name__


def _own_ring_painters(root: QWidget) -> set[str]:
    """The exempted stops actually found inside `root`.

    An exemption nobody uses is dead weight that still hides a class, so the
    list is checked against the application rather than only trusted.
    """
    return {
        type(widget).__name__
        for widget in [root, *root.findChildren(QWidget)]
        if type(widget).__name__ in PAINTS_ITS_OWN_RING
    }


def _focusable(root: QWidget) -> set[str]:
    """The Qt class of every tab stop inside `root`, itself included.

    Item views are dropped here rather than filtered later, because they are
    ringless by design and asserted so by the check above. The other two
    exceptions are dropped by their own class, each for a stated reason.
    """
    found = set()
    for widget in [root, *root.findChildren(QWidget)]:
        tabbable = int(widget.focusPolicy()) & int(Qt.FocusPolicy.TabFocus)
        leaf = type(widget).__name__
        if not tabbable or leaf == NOTHING_TO_PAINT:
            continue
        if leaf in PAINTS_ITS_OWN_RING:
            continue
        if isinstance(widget, QAbstractItemView):
            continue
        found.add(_qt_class(widget))
    return found


@pytest.mark.parametrize("mode", tuple(Mode))
def test_every_control_that_can_be_landed_on_names_a_ring(
    application: QApplication, window, mode: Mode
) -> None:
    """Walked off the real widgets rather than off a list somebody maintains.

    A list would not have caught the checkbox, since whoever forgot the rule
    would have forgotten the list entry with it. The dialogs are built here
    too: both of the application's checkboxes live in one, so a window alone
    would still have passed while the defect stood.
    """
    dialogs = (
        ClosePrompt(window),
        EqualiserDialog(window, Equalisation(), lambda _curve: None),
    )
    controls = _focusable(window)
    painters = _own_ring_painters(window)
    for dialog in dialogs:
        controls |= _focusable(dialog)
        painters |= _own_ring_painters(dialog)
    assert painters == set(PAINTS_ITS_OWN_RING), "every exemption is really used"
    ringed = {selector for selector, _block in ring_rules(stylesheet(mode))}
    for control in sorted(controls):
        assert any(
            re.search(rf"(^|[\s,]){control}[:#\s,]", selector) for selector in ringed
        ), f"{control} can be landed on but names no ring"


@pytest.mark.parametrize("mode", tuple(Mode))
@pytest.mark.parametrize(
    "build_control",
    (lambda parent: StarRating(parent), lambda parent: RingedCheckBox("Keep", parent)),
    ids=PAINTS_ITS_OWN_RING,
)
def test_a_control_exempted_above_really_does_paint_its_own_ring(
    application: QApplication, build_control, mode: Mode
) -> None:
    """Each exemption held to what it claims, in both appearances.

    Rendering runs the widget's own paintEvent, so what is compared is the
    drawing rather than the screen. The stylesheet is applied because one of
    these reads its colours from it and would otherwise have none to paint.

    A second control shares the host so that focus has somewhere else to be.
    A lone focusable widget takes focus the moment it is shown, which makes
    both renders the focused one and the comparison pass while proving nothing.
    """
    application.setStyleSheet(stylesheet(mode))
    host = QWidget()
    row = QHBoxLayout(host)
    elsewhere = QPushButton("elsewhere", host)
    control = build_control(host)
    row.addWidget(elsewhere)
    row.addWidget(control)
    host.show()
    host.activateWindow()
    application.processEvents()
    elsewhere.setFocus()
    application.processEvents()
    assert not control.hasFocus(), "focus is somewhere else to start with"
    unfocused = control.grab().toImage()
    control.setFocus()
    application.processEvents()
    assert control.hasFocus()
    assert control.grab().toImage() != unfocused, "focus changed nothing drawn"
    host.close()


def test_the_ringed_checkbox_still_shows_whether_it_is_ticked(
    application: QApplication,
) -> None:
    """The reason the ring is painted rather than styled, held as a test.

    Naming `::indicator` in the stylesheet hands Qt the whole subcontrol and
    the tick goes with it. Nothing about that is visible in a rule that looks
    perfectly reasonable, so what would catch it is this: a box that cannot be
    told ticked from unticked.
    """
    application.setStyleSheet(stylesheet(Mode.DARK))
    host = QWidget()
    box = RingedCheckBox("Keep", host)
    QHBoxLayout(host).addWidget(box)
    host.show()
    application.processEvents()
    unticked = box.grab().toImage()
    box.setChecked(True)
    application.processEvents()
    assert box.grab().toImage() != unticked, "a tick that cannot be seen is no tick"
    host.close()
