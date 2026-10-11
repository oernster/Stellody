"""The strip along the bottom: rescan and repair, the sound, shuffle and repeat.

Its own strip rather than a place in the tray above, because none of these is
a transport command. They are settings and errands that outlast the track in
hand; they belong where a setting sits. Three quarters of the size of the tray
above it, derived from that tray's own sizes so the two cannot drift apart:
subordinate to the tray without the artwork becoming too small to read.

The right end holds how the music sounds, then how the queue runs: volume and
mute, a rule, the output device, exclusive output and the equalizer, a rule,
then shuffle and repeat. Volume and mute stay
side by side because the two are one thought: how loud, then whether at all.
Rescan and repair sit at the left instead, under the library they act on.
Repair follows rescan because it is the answer to what a rescan finds.

Neither is reached often. A rescan is asked for when something has been added
to the folder, so it is an errand rather than a control of what is playing;
the tray above is what a listener uses while listening. Keeping the two
strips apart by that question, what is playing against what the library holds,
is what decides which strip anything goes on.

The visualiser sits in the middle, between the two groups. It is the one thing
on this strip that is neither a control nor a setting, so it belongs where
nothing is pressed; it is held at the middle the way the tray above holds its
transport. It had a whole band of the window to itself
at first, which was room taken from the library for something that is a small
moving thing rather than a feature anybody looks AT.

The donate button sits outside them at the head of the row, the first thing on
the strip: it belongs to nothing on screen, so it sits where nothing else is
reached by accident. A hairline rules it off from the two beside it, which is
how the tray above separates discovery from the controls that act on the
application.

Every picture here names what a press would DO rather than what the switch is
currently holding, which is the rule the mute switch has always followed. A
cross is a promise to turn something off, never a report that it is off. One
rule across the whole application beats a rule per strip: a listener who has
read one switch has read the rest.

The tooltips follow the pictures, with repeat the one exception. It is the
only control on either strip holding three states rather than two; words
naming just the next press read there as a switch stuck the wrong way round,
so its words name the control instead. The picture still names the press.
"""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QPushButton, QWidget

from stellody.domain.playback import RepeatMode
from stellody.shared import resources
from stellody.ui.covering import CoverSize
from stellody.ui.lift_menu import LiftMenu, Line, fill_choices, pop_up_above
from stellody.ui.queue_switches import QueueSwitches
from stellody.ui.showing_controls import ShowingControls
from stellody.ui.sound_controls import SoundControls
from stellody.ui.theme import HALF
from stellody.ui.tray_metrics import (
    BUTTON_PX,
    ICON_PX,
    SEPARATOR_INSET_PX,
    TRAY_GAP_PX,
    TRAY_MARGIN_PX,
)
from stellody.ui.tray_parts import centred_row, group, icon_button, separator
from stellody.ui.visualisations import (
    NAMES,
    VISUALISATION_TOOLTIP,
    VISUALISATIONS,
    Visualisation,
)
from stellody.ui.visualiser import Visualiser

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


# One wording, one home, kept where the button itself is. The health report's
# own repair control reads it from here, so the two cannot come to say
# different things about one feature.
#
# It names what THIS press does, which is open the screen, rather than what a
# control inside that screen does. It briefly read "Accept the corrections
# library health reports", which is the wording of a button on the screen this
# one opens: a press of this accepts nothing. Shaped like the control beside
# it, which says "Rescan the library", since the two are a pair.
# The promise is made where the gesture is offered rather than only inside the
# screen it opens. "Repair the library" is the one control here that sounds like
# it changes somebody's files; the whole application exists because another
# player did exactly that, so the answer belongs on the button.
REPAIR_TOOLTIP = "Repair the library (your music files are never changed)"
# Said in the tooltip because pressing it leaves the application, which a
# picture of a beer and a coffee does not on its own tell anybody.
DONATE_TOOLTIP = "Buy the author a drink (opens your browser)"


def _small_button(
    parent: QWidget, path, tip: str, on_click: Callable[[], None]
) -> QPushButton:
    """One picture button, matching the tray above at three quarters scale."""
    return icon_button(parent, path, tip, on_click, BOTTOM_BUTTON_PX, BOTTOM_ICON_PX)


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
        toggle_view: Callable[[], None] = lambda: None,
        toggle_cover_size: Callable[[], None] = lambda: None,
        open_equaliser: Callable[[], None] = lambda: None,
        toggle_mute: Callable[[], None] = lambda: None,
        toggle_exclusive: Callable[[], None] = lambda: None,
        set_volume: Callable[[int], None] = lambda _percent: None,
        read_levels=None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("BottomTray")
        # Qt draws a stylesheet BORDER on a plain QWidget only where this
        # attribute is set. Without it the background fills and the border
        # is dropped in silence, which is why the rule in theme.py drew
        # nothing at all. Measured on both trays: unset, every edge pixel
        # comes back surface; set, the first and last rows come back
        # border.
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        # A container is never a stop, so it is said rather than assumed.
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.switches = QueueSwitches(
            self, BOTTOM_BUTTON_PX, BOTTOM_ICON_PX, toggle_shuffle, toggle_repeat
        )
        self.shuffle_button = self.switches.shuffle_button
        self.repeat_button = self.switches.repeat_button
        self.donate_button = _small_button(
            self, resources.donate_icon_path(), DONATE_TOOLTIP, open_donation
        )
        self.separator = separator(self, BOTTOM_SEPARATOR_HEIGHT_PX)
        self.rescan_button = _small_button(
            self, resources.rescan_icon_path(), "Rescan the library", rescan
        )
        self.repair_button = _small_button(
            self, resources.library_health_icon_path(), REPAIR_TOOLTIP, repair_library
        )
        # Off until the library has reported: `offer_repairs` turns it on once
        # there is a correction to accept or an accepted one to take back.
        self.repair_button.setEnabled(False)
        # What the library is SHOWN as, moved down from the tray above. Three
        # more pictures crowded that end of a window nobody has to maximise,
        # while this strip has room going spare. They stay in their own order
        # and simply continue the errands already here.
        self.showing_separator = separator(self, BOTTOM_SEPARATOR_HEIGHT_PX)
        self.showing = ShowingControls(
            self,
            BOTTOM_BUTTON_PX,
            BOTTOM_ICON_PX,
            TRAY_GAP_PX,
            toggle_view=toggle_view,
            toggle_cover_size=toggle_cover_size,
        )
        # How the music is DRAWN closes the left group, after how the library
        # is: both change what is on show, so the two sit side by side.
        # A press lifts the list of styles, as the output button lifts its
        # devices; `lift_menu.py` is the one home for how either behaves.
        self.visualisation_separator = separator(self, BOTTOM_SEPARATOR_HEIGHT_PX)
        self.visualisation_menu = LiftMenu(self)
        self.visualisation_button = _small_button(
            self,
            resources.visualisations_icon_path(),
            VISUALISATION_TOOLTIP,
            lambda: pop_up_above(self.visualisation_menu, self.visualisation_button),
        )
        self.sound = SoundControls(
            self,
            BOTTOM_BUTTON_PX,
            BOTTOM_ICON_PX,
            TRAY_GAP_PX,
            toggle_mute=toggle_mute,
            set_volume=set_volume,
            open_equaliser=open_equaliser,
            toggle_exclusive=toggle_exclusive,
            separator_height_px=BOTTOM_SEPARATOR_HEIGHT_PX,
        )
        # How the music sounds is a different question from how the queue
        # runs, so a rule stands between the sound and the two switches.
        self.sound_separator = separator(self, BOTTOM_SEPARATOR_HEIGHT_PX)
        # As tall as a button beside it, centred against them: the tallest it
        # can stand without making the strip itself taller. It was half that
        # until Oliver asked for more of it on 2026-10-11.
        self.visualiser = Visualiser(self, BOTTOM_BUTTON_PX)
        if read_levels is not None:
            self.visualiser.read_levels_from(read_levels)
        # The visualiser at the middle of the strip rather than the middle of
        # what the two groups leave over: see centred_row for why those differ.
        # What the library is drawn as is a different errand from rescanning
        # and repairing it, so a rule stands between the two groups exactly as
        # one stands after the donation mark.
        centred_row(
            self,
            BOTTOM_MARGIN_PX,
            TRAY_GAP_PX,
            group(
                TRAY_GAP_PX,
                self.donate_button,
                self.separator,
                *self.library_stops(),
                self.showing_separator,
                self.showing,
                self.visualisation_separator,
                self.visualisation_button,
            ),
            group(TRAY_GAP_PX, self.visualiser),
            group(
                TRAY_GAP_PX,
                self.sound,
                self.sound_separator,
                *self.switch_stops(),
            ),
        )
        self.set_shuffled(False)
        self.set_repeat(RepeatMode.OFF)

    def ring_stops(self) -> tuple[QPushButton, ...]:
        """This tray's controls, left to right as they are drawn.

        The repair control is named here while it is disabled, so the ring
        picks it up on the day it works without the order being revisited. Qt
        skips a disabled stop, so naming it costs nothing until then.
        """
        return (
            self.donate_button,
            *self.library_stops(),
            *self.showing.stops(),
            self.visualisation_button,
            *self.sound.stops(),
            *self.switch_stops(),
        )

    def library_stops(self) -> tuple[QPushButton, ...]:
        """The library errands at the left end, left to right as they are drawn."""
        return (self.rescan_button, self.repair_button)

    def switch_stops(self) -> tuple[QPushButton, ...]:
        """The settings at the right end, left to right as they are drawn."""
        return self.switches.stops()

    def set_showing_covers(self, covers: bool) -> None:
        """Say what pressing the view toggle would do from here."""
        self.showing.set_showing_covers(covers)

    def set_next_cover_size(self, size: CoverSize) -> None:
        """Show the size a press would move to."""
        self.showing.set_next_cover_size(size)

    def show_visualisations(
        self, chosen: Visualisation, choose: Callable[[Visualisation], None]
    ) -> None:
        """Put every style in the list the visualiser button lifts, ticking one."""
        fill_choices(
            self.visualisation_menu,
            tuple(
                Line(NAMES[style], style is chosen, lambda style=style: choose(style))
                for style in VISUALISATIONS
            ),
        )

    def set_percent(self, percent: int) -> None:
        """Remember where the volume is, so the slider opens showing it."""
        self.sound.set_percent(percent)

    def set_exclusive(self, exclusive: bool) -> None:
        """Show what pressing the output switch would do from here."""
        self.sound.set_exclusive(exclusive)

    def refuse_exclusive(self, reason: str) -> None:
        """Stand the output switch down where the platform offers no route."""
        self.sound.refuse_exclusive(reason)

    def hold_exclusive(self, reason: str) -> None:
        """Stand the output switch down for the song in hand where there is why."""
        self.sound.hold_exclusive(reason)

    def set_muted(self, muted: bool) -> None:
        """Show what pressing the mute switch would do from here."""
        self.sound.set_muted(muted)

    def set_shuffled(self, shuffled: bool) -> None:
        """Light the shuffle switch while the queue is scattered."""
        self.switches.set_shuffled(shuffled)

    def set_repeat(self, repeat: RepeatMode) -> None:
        """Show which of the three repeat states the switch is holding."""
        self.switches.set_repeat(repeat)

    def offer_repairs(self, available: bool) -> None:
        """Say whether there is anything for the repair control to act on.

        Answered here rather than inside the errand, so this button and the
        menu entry beside it cannot come to disagree, which is the rule the
        rescan control already follows.
        """
        self.repair_button.setEnabled(available)
