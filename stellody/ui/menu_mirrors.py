"""The menu entries that stand for a picture button on one of the two strips.

Oliver asked on 2026-09-16 for every button to be reachable from the menu bar
as well: the view and the sleeve size, repair, mute, shuffle, repeat, discovery,
search and filter, with search and filter under an Edit menu of their own. The
transport followed the same day, on a Control menu right of Sound; exclusive
output joined Sound on 2026-09-18, the output device beside it. The volume
stays off the menus by the same ruling, since a slider is not an entry.

Each entry reads its state from the thing it stands for, at the moment its menu
opens, rather than being kept in step as that thing changes. Whether it can act
is the button's own answer; whether it is ticked is the transport's or the
window's. So an entry and its button cannot come to disagree, which is the rule
Rescan already follows from the other direction.

The output device is the one exception, for a reason of its own: its lines are
the devices themselves, which change while a list is open, so both lists are
refilled from the transport by one function whenever they change.
"""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtGui import QAction, QActionGroup
from PySide6.QtWidgets import QMenu

from stellody.domain.playback import OutputMode, RepeatMode
from stellody.ui.covering import COVER_SIZES
from stellody.ui.menus import menu_action
from stellody.ui.showing_controls import SIZE_NAMES

# What each repeat state is called where it is chosen by name rather than
# stepped through with a switch.
REPEAT_NAMES = {
    RepeatMode.OFF: "Off",
    RepeatMode.ALBUM: "Album",
    RepeatMode.ONE: "One track",
}
PLAY_LABEL = "&Play"
PAUSE_LABEL = "&Pause"


class MenuMirrors:
    """The window's half of offering its buttons on the menu bar too."""

    def _mirror_file(self, file_menu: QMenu) -> None:
        """Repair and discovery, beside the other errands on the library."""
        self._repair_action = menu_action(
            file_menu, self, "Re&pair the library...", self.repair_library
        )
        self._discover_action = menu_action(
            file_menu, self, "&Discover new music...", self.open_discovery
        )
        file_menu.aboutToShow.connect(self._show_mirrored_state)

    def _build_edit_menu(self) -> None:
        """Search and filter: the two ways of narrowing what is on show."""
        edit_menu = self.menuBar().addMenu("&Edit")
        self._search_action = menu_action(
            edit_menu, self, "&Search the library", self.toggle_search, checkable=True
        )
        self._filter_action = menu_action(
            edit_menu, self, "&Filter the library...", self.open_filter, checkable=True
        )
        edit_menu.aboutToShow.connect(self._show_mirrored_state)

    def _mirror_view(self, view_menu: QMenu) -> None:
        """The sleeves or the list, then how large a sleeve is drawn."""
        showing = QActionGroup(self)
        self._covers_action = _chosen(
            view_menu, self, showing, "Album &art", lambda: self.show_covers(True)
        )
        self._list_action = _chosen(
            view_menu, self, showing, "Lis&t", lambda: self.show_covers(False)
        )
        self._size_menu = view_menu.addMenu("Album art s&ize")
        sizes = QActionGroup(self)
        self._size_actions = {
            size: _chosen(
                self._size_menu,
                self,
                sizes,
                SIZE_NAMES[size].capitalize(),
                lambda size=size: self.show_cover_size_choice(size),
            )
            for size in COVER_SIZES
        }
        view_menu.aboutToShow.connect(self._show_mirrored_state)

    def _mirror_sound(self, sound_menu: QMenu) -> None:
        """Exclusive output, the output device, mute, then how the queue runs.

        Exclusive output follows the equalizer, since both act on the stream,
        which is how the strip groups them after its rule. Asked for by Oliver
        on 2026-09-18, the switch having arrived after the menus did. The
        output device joined them the same day, beside exclusive output
        (`OUTPUTS.md` FR-O17) and after it, so exclusive output still sits
        beside the equalizer. Its lines are the strip's list, filled by one
        function whenever the choice or the devices change, which is every
        way they can; `ChoosingOutputs.show_outputs` fills both.
        """
        self._exclusive_action = menu_action(
            sound_menu,
            self,
            "E&xclusive output",
            self.toggle_exclusive,
            checkable=True,
        )
        self._output_menu = sound_menu.addMenu("Output &device")
        sound_menu.addSeparator()
        self._mute_action = menu_action(
            sound_menu, self, "&Mute", self.toggle_mute, checkable=True
        )
        sound_menu.addSeparator()
        self._shuffle_action = menu_action(
            sound_menu, self, "&Shuffle", self.toggle_shuffle, checkable=True
        )
        self._repeat_menu = sound_menu.addMenu("&Repeat")
        modes = QActionGroup(self)
        self._repeat_actions = {
            mode: _chosen(
                self._repeat_menu,
                self,
                modes,
                REPEAT_NAMES[mode],
                lambda mode=mode: self.choose_repeat(mode),
            )
            for mode in RepeatMode
        }
        sound_menu.aboutToShow.connect(self._show_mirrored_state)

    def _build_control_menu(self) -> None:
        """The transport, in the order the right click menu offers it."""
        control_menu = self.menuBar().addMenu("&Control")
        self._play_action = menu_action(
            control_menu, self, PLAY_LABEL, self.toggle_playback
        )
        self._stop_action = menu_action(control_menu, self, "&Stop", self.stop_playback)
        control_menu.addSeparator()
        self._previous_action = menu_action(
            control_menu, self, "Pre&vious track", self.previous_track
        )
        self._next_action = menu_action(
            control_menu, self, "&Next track", self.next_track
        )
        control_menu.aboutToShow.connect(self._show_mirrored_state)

    def _show_mirrored_state(self) -> None:
        """Read every mirrored entry's state off what it stands for."""
        tray, strip = self._tray, self._bottom_tray
        self._repair_action.setEnabled(strip.repair_button.isEnabled())
        self._discover_action.setEnabled(tray.discover_button.isEnabled())
        self._search_action.setChecked(tray.searching)
        self._filter_action.setEnabled(tray.filter_button.isEnabled())
        self._filter_action.setChecked(tray.filter_button.isChecked())
        covers = self.showing_covers
        self._covers_action.setChecked(covers)
        self._list_action.setChecked(not covers)
        sizing = strip.showing.size_button.isEnabled()
        self._size_menu.menuAction().setEnabled(sizing)
        for size, action in self._size_actions.items():
            action.setEnabled(sizing)
            action.setChecked(size is self._cover_size)
        # Offered where the switch is: a platform, a device or a lossy song
        # that stands it down takes the entry down with it.
        self._exclusive_action.setEnabled(strip.sound.exclusive_button.isEnabled())
        self._exclusive_action.setChecked(
            self._transport.output_mode is OutputMode.EXCLUSIVE
        )
        self._mute_action.setChecked(self._transport.muted)
        self._shuffle_action.setChecked(self._transport.shuffled)
        for mode, action in self._repeat_actions.items():
            action.setChecked(mode is self._transport.repeat)
        # Named for what a press does, as the button's own picture is.
        playing = self._transport.playing
        self._play_action.setText(PAUSE_LABEL if playing else PLAY_LABEL)
        for action, button in (
            (self._play_action, tray.play_button),
            (self._stop_action, tray.stop_button),
            (self._previous_action, tray.previous_button),
            (self._next_action, tray.next_button),
        ):
            action.setEnabled(button.isEnabled())


def _chosen(
    menu: QMenu, window, group: QActionGroup, label: str, choose: Callable[[], None]
) -> QAction:
    """One of a set of entries only one of which can be ticked at a time.

    The tick Qt puts on a press is only what the press asked for; the entry is
    ticked again from the real state whenever its menu next opens.
    """
    action = menu_action(menu, window, label, lambda _checked: choose(), True)
    group.addAction(action)
    return action
