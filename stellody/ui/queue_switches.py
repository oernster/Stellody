"""The two switches at the right end of the bottom strip: shuffle and repeat.

How the queue runs, rather than how the music sounds or what the library is
shown as. Split from `bottom_tray.py`, which holds the strip they sit on, once
that file reached the line cap's danger band; the switches' pictures and words
are a concern of their own.

Every picture here names what a press would DO rather than what the switch is
currently holding, which is the rule the mute switch has always followed. A
cross is a promise to turn something off, never a report that it is off.
"""

from __future__ import annotations

import pathlib
from collections.abc import Callable

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QPushButton, QWidget

from stellody.domain.playback import RepeatMode
from stellody.shared import resources
from stellody.ui.icons import plain_icon, struck_through
from stellody.ui.tray_parts import icon_button

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


class QueueSwitches:
    """Shuffle then repeat, built on the strip that lays them out."""

    def __init__(
        self,
        parent: QWidget,
        button_px: int,
        icon_px: int,
        toggle_shuffle: Callable[[], None],
        toggle_repeat: Callable[[], None],
    ) -> None:
        self._icon_px = icon_px
        self.shuffle_button = self._switch(
            parent, "Turn shuffle on", toggle_shuffle, button_px
        )
        self.repeat_button = self._switch(
            parent, REPEAT_TOOLTIP, toggle_repeat, button_px
        )

    def _switch(
        self, parent: QWidget, tip: str, on_click: Callable[[], None], button_px: int
    ) -> QPushButton:
        """One picture button that stays down while whatever it names is on.

        Checkable carries no paint of its own here, since the artwork says the
        state. It is kept so anything reading the widget rather than looking at
        it is still told which switches are engaged.
        """
        button = icon_button(parent, None, tip, on_click, button_px, self._icon_px)
        button.setCheckable(True)
        return button

    def stops(self) -> tuple[QPushButton, ...]:
        """The two switches, left to right as they are drawn."""
        return (self.shuffle_button, self.repeat_button)

    def _state_icon(self, path: pathlib.Path | None, becomes_on: bool) -> QIcon:
        """The picture a press would land on: the artwork, else it crossed out.

        Named for the destination rather than the current state, so the cross
        reads as an offer to switch off rather than as a report of being off.
        """
        if becomes_on:
            return plain_icon(path)
        return struck_through(path, resources.negative_icon_path(), self._icon_px)

    def set_shuffled(self, shuffled: bool) -> None:
        """Light the shuffle switch while the queue is scattered; say the press.

        The picture shows where a press would leave it, so a lit switch wears
        the cross that offers to put it out.
        """
        button = self.shuffle_button
        button.setIcon(self._state_icon(resources.shuffle_icon_path(), not shuffled))
        button.setChecked(shuffled)
        button.setToolTip(f"Turn shuffle {'off' if shuffled else 'on'}")

    def set_repeat(self, repeat: RepeatMode) -> None:
        """Show which of the three repeat states the switch is holding.

        The picture is the state a press would move to, read off the mode
        itself rather than from a second table, so the picture and the press
        cannot come to disagree. The tooltip is not touched: it names the
        control rather than the state.
        """
        following = repeat.after
        if following is RepeatMode.OFF:
            icon = self._state_icon(resources.repeat_icon_path(), False)
        else:
            icon = plain_icon(REPEAT_ICONS[following]())
        self.repeat_button.setIcon(icon)
        self.repeat_button.setChecked(repeat.repeats)
