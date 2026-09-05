"""No control tells a listener that what it does has not been built.

A tooltip outlives the state it was written for. The repair control shipped
enabled while still saying "not built yet", because enabling a feature and
rewording the thing attached to it are two edits and only one of them was made.

Swept rather than checked where it was reported, which is the rule the menu bar
already follows: fixing the one that was noticed leaves every other one
unexamined; whoever forgets to reword a tooltip forgets the list entry with it.
"""

from __future__ import annotations

import pytest
from conftest import RecordingPlayer
from PySide6.QtWidgets import QWidget
from tray_support import RememberingStore, build

from stellody.domain.equalising import Equalisation
from stellody.ui.close_prompt import ClosePrompt
from stellody.ui.equaliser import EqualiserDialog
from stellody.ui.health import HealthDialog

# Phrases that promise a thing does not work yet. The bare word "yet" is not
# among them: "nothing has played yet" is an honest thing for a control to say.
UNBUILT_PHRASES = (
    "not built",
    "not yet built",
    "not implemented",
    "coming soon",
    "unbuilt",
    "todo",
    "to be done",
    "placeholder",
)


def _tooltips(root: QWidget) -> list[tuple[str, str]]:
    """Every tooltip under a widget, against the control that carries it.

    A list rather than a dictionary, because most controls here carry no object
    name: keyed by type and name, two unnamed buttons collide and one tooltip
    is dropped in silence, so the sweep would pass over an offence it had
    actually reached. Found by planting one on a strip that had just gained
    three more unnamed buttons.
    """
    found = [
        (f"{type(widget).__name__}({widget.objectName() or '?'})", widget.toolTip())
        for widget in root.findChildren(QWidget)
        if widget.toolTip()
    ]
    if root.toolTip():
        found.append((type(root).__name__, root.toolTip()))
    return found


def _offences(root: QWidget) -> list[str]:
    """Every tooltip here that says its feature is not built."""
    return [
        f"{where}: {tip!r}"
        for where, tip in _tooltips(root)
        for phrase in UNBUILT_PHRASES
        if phrase in tip.casefold()
    ]


@pytest.fixture
def window(application):
    """A real window, closed however the test ends."""
    made = build(RememberingStore(), RecordingPlayer())
    yield made
    made.close()


def test_no_control_in_the_window_says_it_is_not_built(window) -> None:
    assert _offences(window) == []


def test_no_control_in_a_dialog_says_it_is_not_built(application, window) -> None:
    """The dialogs are swept too: the control that failed this lived in one."""
    dialogs = (
        ClosePrompt(window),
        EqualiserDialog(window, Equalisation(), lambda _curve: None),
        HealthDialog((), window),
        HealthDialog((), window, can_repair=True),
    )
    for dialog in dialogs:
        assert _offences(dialog) == [], type(dialog).__name__
        dialog.deleteLater()


def test_the_sweep_bites(window) -> None:
    """A guard never seen to fail is not yet a guard, so one is planted here."""
    window._bottom_tray.repair_button.setToolTip("Repair the library (not built yet)")
    try:
        assert _offences(window), "a planted claim must be found"
    finally:
        window._bottom_tray.repair_button.setToolTip("")


def test_the_sweep_reads_the_real_words(window) -> None:
    """Guards the sweep itself: it must be looking at actual tooltips."""
    tips = _tooltips(window)
    assert tips, "a window with no tooltips at all means the walk found nothing"
