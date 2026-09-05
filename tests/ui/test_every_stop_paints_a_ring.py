"""Every control that can be landed on paints a ring.

The other half of the ring rules, in `test_focus_rings.py`, says which classes
must NOT ring. This says every class that CAN be landed on must, which is the
one defect that check cannot see: a control shipped with no rule at all takes
focus and reports nothing.
"""

from __future__ import annotations

import re

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QHBoxLayout,
    QPushButton,
    QWidget,
)
from ring_support import build_ring_window, ring_rules

from stellody.domain.equalising import Equalisation
from stellody.ui.close_prompt import ClosePrompt
from stellody.ui.equaliser import EqualiserDialog
from stellody.ui.menu_bar import RingedMenuBar
from stellody.ui.picture_controls import SizeButton
from stellody.ui.ringed_check import RingedCheckBox
from stellody.ui.stars import StarRating
from stellody.ui.theme import Mode, stylesheet


@pytest.fixture
def window(application: QApplication):
    """The real main window, built as both ring suites build it."""
    yield from build_ring_window(application)


# A control that takes focus and paints nothing is the one defect the two
# checks above cannot see: they say which classes must NOT ring, while this
# says every class that CAN be landed on must. A checkbox shipped with no rule
# at all, so Tab stopped on it and nothing on screen reported that it had.
# Item views are the sanctioned exception and are listed as such rather than
# quietly passing: their current row is the indicator.
# Stops the stylesheet is right not to name. A zero-size holder has nothing to
# paint a ring on. The other two paint their own and say in their modules why
# the sheet cannot do it for them: five glyphs standing for one value must ring
# once rather than five times; a checkbox's square belongs to Qt, which takes
# the whole subcontrol over the moment a sheet names it. Each is listed here
# rather than passing quietly, then each is proved below.
NOTHING_TO_PAINT = "_NeutralStart"
PAINTS_ITS_OWN_RING = (
    "StarRating",
    "RingedCheckBox",
    "SizeButton",
    # Each menu TITLE is a stop, so the ring goes round the one the keyboard
    # is on. A stylesheet cannot say that: a bar-wide rule draws a line past
    # the last menu and names the bar rather than the title.
    "RingedMenuBar",
)


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


def _a_menu_bar(parent: QWidget) -> RingedMenuBar:
    """A menu bar with titles to ring, since a bare one has nothing to draw."""
    bar = RingedMenuBar(parent)
    for title in ("&File", "&View"):
        bar.addMenu(title)
    return bar


@pytest.mark.parametrize("mode", tuple(Mode))
@pytest.mark.parametrize(
    "build_control",
    (
        lambda parent: StarRating(parent),
        lambda parent: RingedCheckBox("Keep", parent),
        lambda parent: SizeButton(parent),
        _a_menu_bar,
    ),
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
    # The tab reason rather than any reason: the ring says the KEYBOARD is
    # here; one of these lights only for a keyboard arrival, because a
    # click on a menu title already opens the menu it landed on.
    control.setFocus(Qt.FocusReason.TabFocusReason)
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
