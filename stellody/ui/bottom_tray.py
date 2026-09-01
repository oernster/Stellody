"""The strip along the bottom: rescan and repair, shuffle and repeat.

Its own strip rather than a place in the tray above, because none of these is
a transport command. They are settings and errands that outlast the track in
hand; they belong where a setting sits. Three quarters of the size of the tray
above it, derived from that tray's own sizes so the two cannot drift apart:
subordinate to the tray without the artwork becoming too small to read.

The volume is the exception; it sits in the tray above beside the mute
switch. The two are one thought: how loud, then whether at all. Splitting them
across two strips meant crossing the window to do half of it.

The switches sit at the right end, under About and the appearance toggle,
which is where the application's own controls already are. Rescan and repair
sit at the left instead, under the library they act on. Repair follows rescan
because it is the answer to what a rescan finds.

Neither is reached often. A rescan is asked for when something has been added
to the folder, so it is an errand rather than a control of what is playing;
the tray above is what a listener uses while listening. Keeping the two
strips apart by that question, what is playing against what the library holds,
is what decides which strip anything goes on.

The visualiser sits in the middle, between the two groups. It is the one thing
on this strip that is neither a control nor a setting, so it belongs where
nothing is pressed; a stretch either side is what centres it, which is how the
tray above centres its transport. It had a whole band of the window to itself
at first, which was room taken from the library for something that is a small
moving thing rather than a feature anybody looks AT.

The donate button sits outside them at the very end of the row: it belongs to
nothing on screen, so it sits where nothing else is reached by accident. A
hairline rules it off from the two beside it, which is how the tray above
separates the mute switch from the controls that act on the application.

Every picture here names what a press would DO rather than what the switch is
currently holding, which is the rule the mute switch in the tray above has
always followed. A cross is a promise to turn something off, never a report
that it is off. One rule across the whole application beats a rule per strip:
a listener who has read one switch has read the rest.

The tooltips follow the pictures, with repeat the one exception. It is the
only control on either strip holding three states rather than two; words
naming just the next press read there as a switch stuck the wrong way round,
so its words name the control instead. The picture still names the press.
"""

from __future__ import annotations

import pathlib
from collections.abc import Callable

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QHBoxLayout, QPushButton, QWidget

from stellody.domain.playback import RepeatMode
from stellody.shared import resources
from stellody.ui.icons import plain_icon, struck_through
from stellody.ui.toolbar import (
    BUTTON_PX,
    ICON_PX,
    SEPARATOR_INSET_PX,
    SEPARATOR_WIDTH_PX,
    TRAY_GAP_PX,
    TRAY_MARGIN_PX,
)
from stellody.ui.tray_parts import icon_button, separator
from stellody.ui.visualiser import Visualiser

HALF = 2
# Three quarters of the tray above. Expressed against that tray's own sizes so
# the two cannot drift apart when either is retuned.
SWITCH_NUMERATOR = 3
SWITCH_DENOMINATOR = 4
BOTTOM_BUTTON_PX = BUTTON_PX * SWITCH_NUMERATOR // SWITCH_DENOMINATOR
BOTTOM_ICON_PX = ICON_PX * SWITCH_NUMERATOR // SWITCH_DENOMINATOR
BOTTOM_MARGIN_PX = TRAY_MARGIN_PX // HALF
# The hairline is inset from this strip's own button in the same proportion as
# the one in the tray above, so the two read as the same rule at two scales.
BOTTOM_SEPARATOR_INSET_PX = SEPARATOR_INSET_PX * SWITCH_NUMERATOR // SWITCH_DENOMINATOR
BOTTOM_SEPARATOR_HEIGHT_PX = (
    BOTTOM_BUTTON_PX - BOTTOM_SEPARATOR_INSET_PX - BOTTOM_SEPARATOR_INSET_PX
)


# Keyed by the state a press LANDS on, not the one it leaves. Repeating the
# album is the plain wheel and holding one track is the numbered wheel;
# arriving back at off is the wheel crossed out, composed rather than drawn.
REPEAT_ICONS = {
    RepeatMode.ALBUM: resources.repeat_icon_path,
    RepeatMode.ONE: resources.repeat_one_icon_path,
}
# The one control on either strip whose words name the control rather than the
# next press. Every other switch here holds two states, where naming the press
# tells the whole story. This one holds three, where naming only the next
# press reads as a switch that has got itself the wrong way round: offered "Repeat
# one track" while the album is already repeating looks like a refusal to turn
# off rather than the second step of a cycle. So the words say which control
# this is and the picture keeps saying what a press would do, which is the half
# of the rule that actually needs a glance rather than a hover. One wording for
# all three states also means a tooltip that does not rewrite itself under the
# pointer while somebody is reading it.
REPEAT_TOOLTIP = "Repeat mode"
# One wording, one home, kept where the button itself is. The health report's
# own repair control reads it from here, so the two cannot come to say
# different things about the same unbuilt feature. What that report lists can
# be worked out, since resolution already happens on load; nothing yet lets a
# correction be accepted and kept, so there is nothing for this to do.
REPAIR_TOOLTIP = "Repair what library health reports (not built yet)"
# Said in the tooltip because pressing it leaves the application, which a
# picture of a beer and a coffee does not on its own tell anybody.
DONATE_TOOLTIP = "Buy the author a drink (opens your browser)"


def _small_button(
    parent: QWidget, path, tip: str, on_click: Callable[[], None]
) -> QPushButton:
    """One picture button, matching the tray above at three quarters scale."""
    return icon_button(parent, path, tip, on_click, BOTTOM_BUTTON_PX, BOTTOM_ICON_PX)


def _state_icon(path: pathlib.Path | None, becomes_on: bool) -> QIcon:
    """The picture a press would land on: the artwork, else it crossed out.

    Named for the destination rather than the current state, so the cross
    reads as an offer to switch off rather than as a report of being off.
    """
    if becomes_on:
        return plain_icon(path)
    return struck_through(path, resources.negative_icon_path(), BOTTOM_ICON_PX)


def _repeat_icon(repeat: RepeatMode) -> QIcon:
    """The state a press would move to, which nothing else has to be told.

    The cycle is read off the mode itself rather than from a second table,
    so the picture and the press cannot come to disagree.
    """
    following = repeat.after
    if following is RepeatMode.OFF:
        return _state_icon(resources.repeat_icon_path(), False)
    return plain_icon(REPEAT_ICONS[following]())


def _switch_button(
    parent: QWidget, tip: str, on_click: Callable[[], None]
) -> QPushButton:
    """One picture button that stays down while whatever it names is on.

    Checkable carries no paint of its own here, since the artwork says the
    state. It is kept so anything reading the widget rather than looking at
    it is still told which switches are engaged.
    """
    button = _small_button(parent, None, tip, on_click)
    button.setCheckable(True)
    return button


class BottomTray(QWidget):
    """The strip along the bottom, holding the settings that outlast a track."""

    def __init__(
        self,
        parent: QWidget,
        toggle_shuffle: Callable[[], None] = lambda: None,
        toggle_repeat: Callable[[], None] = lambda: None,
        open_donation: Callable[[], None] = lambda: None,
        rescan: Callable[[], None] = lambda: None,
        repair_library: Callable[[], None] = lambda: None,
        read_levels=None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("BottomTray")
        # A container is never a stop, so it is said rather than assumed.
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.shuffle_button = _switch_button(self, "Turn shuffle on", toggle_shuffle)
        self.repeat_button = _switch_button(self, REPEAT_TOOLTIP, toggle_repeat)
        self.donate_button = _small_button(
            self, resources.donate_icon_path(), DONATE_TOOLTIP, open_donation
        )
        self.separator = separator(self, SEPARATOR_WIDTH_PX, BOTTOM_SEPARATOR_HEIGHT_PX)
        self.rescan_button = _small_button(
            self, resources.rescan_icon_path(), "Rescan the library", rescan
        )
        self.repair_button = _small_button(
            self, resources.library_health_icon_path(), REPAIR_TOOLTIP, repair_library
        )
        # Nothing to press yet: what each issue should become is worked out on
        # every load; there is nowhere to keep a correction once accepted.
        self.repair_button.setEnabled(False)
        # Half the height of a button beside it, centred against them: it
        # is something to notice out of the corner of an eye rather than a
        # sixth control, so it should not stand as tall as the things that are.
        self.visualiser = Visualiser(self, BOTTOM_BUTTON_PX // HALF)
        if read_levels is not None:
            self.visualiser.read_levels_from(read_levels)
        row = QHBoxLayout(self)
        row.setContentsMargins(
            BOTTOM_MARGIN_PX, BOTTOM_MARGIN_PX, BOTTOM_MARGIN_PX, BOTTOM_MARGIN_PX
        )
        row.setSpacing(TRAY_GAP_PX)
        row.addWidget(self.donate_button)
        row.addWidget(self.separator)
        for button in self.library_stops():
            row.addWidget(button)
        # A stretch either side of the visualiser is what centres it, whatever
        # the window is widened to. What changes the library sits under the
        # library; the settings finish at the right edge under the
        # application's other controls.
        row.addStretch()
        row.addWidget(self.visualiser, 0, Qt.AlignmentFlag.AlignVCenter)
        row.addStretch()
        for button in self.switch_stops():
            row.addWidget(button)
        self.set_shuffled(False)
        self.set_repeat(RepeatMode.OFF)

    def ring_stops(self) -> tuple[QPushButton, ...]:
        """This tray's controls, left to right as they are drawn.

        The repair control is named here while it is disabled, so the ring
        picks it up on the day it works without the order being revisited. Qt
        skips a disabled stop, so naming it costs nothing until then.
        """
        return (self.donate_button, *self.library_stops(), *self.switch_stops())

    def library_stops(self) -> tuple[QPushButton, ...]:
        """The library errands at the left end, left to right as they are drawn."""
        return (self.rescan_button, self.repair_button)

    def switch_stops(self) -> tuple[QPushButton, ...]:
        """The settings at the right end, left to right as they are drawn."""
        return (self.shuffle_button, self.repeat_button)

    def set_shuffled(self, shuffled: bool) -> None:
        """Light the shuffle switch while the queue is scattered."""
        self._show_switch(
            self.shuffle_button, resources.shuffle_icon_path(), shuffled, "shuffle"
        )

    def set_repeat(self, repeat: RepeatMode) -> None:
        """Show which of the three repeat states the switch is holding.

        The tooltip is not touched: it names the control rather than the state,
        so there is nothing here for a change of state to rewrite.
        """
        self.repeat_button.setIcon(_repeat_icon(repeat))
        self.repeat_button.setChecked(repeat.repeats)

    def _show_switch(self, button: QPushButton, path, on: bool, name: str) -> None:
        """Light one switch while it is on; say what a press would do.

        The picture shows where a press would leave it, so a lit switch wears
        the cross that offers to put it out and nothing behind the artwork
        has to change for the state to be read.
        """
        button.setIcon(_state_icon(path, not on))
        button.setChecked(on)
        button.setToolTip(f"Turn {name} {'off' if on else 'on'}")
