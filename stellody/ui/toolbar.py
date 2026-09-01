"""The icon tray under the menus.

Picture-only buttons in reading order: choose the music folder, rescan it,
repair what the rescan reports and search it on the left, the transport
centred, then the volume, the mute switch, the appearance toggle and About on
the right. The library buttons repeat something the menus already offer, so
they add reach rather than capability; nothing here owns any state of its own.

Search is the one place a box joins the pictures. The button carries the
magnifier and the box appears beside it only while searching, so the tray
reads as pictures until somebody asks it not to. Filtering happens as the box
is typed into, which is why the button opens the box rather than running
anything: there would be nothing for a second press to do.

Repair sits beside rescan because it is the answer to what a rescan finds.
It was down on the bottom strip, which put it among the
settings that outlast a track rather than beside the control it follows from.

Mute is ruled off from the two buttons after it. It acts on what is playing
while they act on the application, so a line says they are different kinds of
thing; the alternative is a run of eight buttons that all read as one group.

Every picture here says what a press would DO rather than what is the case:
the appearance toggle shows the appearance it would move to; the view toggle
names the view it would move to; the mute switch is struck through while the
sound is on, because that press is the one that silences it.

The transport is centred because it is the one group that is about the track
rather than about the library; also because a play button in the corner of a
window is a play button nobody finds.

Volume sits immediately left of mute because the two are one thought: how
loud, then whether at all. It opens a slider rather than spending a strip of
window on a bar touched twice a session; that slider lives in `volume.py`, so
the button can sit wherever it reads best without the slider following it
around.

The tray itself is a container, so it never takes focus and never paints a ring.
Its buttons are controls and wear the app's three ring states.
"""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLineEdit,
    QMenu,
    QPushButton,
    QWidget,
)

from stellody.shared import resources
from stellody.ui.covering import CoverSize
from stellody.ui.icons import plain_icon, struck_through
from stellody.ui.showing_controls import ShowingControls
from stellody.ui.theme import Mode
from stellody.ui.tray_parts import icon_button, separator
from stellody.ui.volume import DEFAULT_PERCENT, VolumeSlider

# The button is a way in to several things rather than one thing, so it is
# named for the menu it opens rather than for the entry that used to be all
# of it. What each entry does is said by the entry.
HELP_TOOLTIP = "Help"
ABOUT_ENTRY = "About"
UPDATES_ENTRY = "Check for updates"

ICON_PX = 60
BUTTON_PX = 91
TRAY_MARGIN_PX = 6
TRAY_GAP_PX = 6
SEPARATOR_WIDTH_PX = 1
# The line stops short of the tray's own edges, so it reads as a division
# between buttons rather than as a border on the tray.
SEPARATOR_INSET_PX = 12
SEPARATOR_HEIGHT_PX = BUTTON_PX - SEPARATOR_INSET_PX - SEPARATOR_INSET_PX
# One wording, one home. The dialog's own repair control reads it from here, so
# the two cannot come to say different things about the same unbuilt feature.
REPAIR_TOOLTIP = "Repair what library health reports (not built yet)"
# Wide enough for an album title rather than for a word, since that is what
# somebody types when they are looking for one.
SEARCH_BOX_PX = 260
# Sized against the buttons beside it rather than against a dialog field:
# a default line edit is a third of a tray button and reads as a mistake.
SEARCH_BOX_HEIGHT_PX = 48
SEARCH_PLACEHOLDER = "Album, artist or track"


def _icon_button(parent: QWidget, path, tip: str, on_click: Callable) -> QPushButton:
    """One picture-only button at this tray's own size."""
    return icon_button(parent, path, tip, on_click, BUTTON_PX, ICON_PX)


class LibraryTray(QWidget):
    """The strip of icon buttons that sits between the menus and the library."""

    def __init__(
        self,
        parent: QWidget,
        choose_folder: Callable[[], None],
        rescan: Callable[[], None],
        toggle_theme: Callable[[], None],
        show_about: Callable[[], None],
        check_for_updates: Callable[[], None] = lambda: None,
        repair_library: Callable[[], None] = lambda: None,
        toggle_search: Callable[[], None] = lambda: None,
        search_changed: Callable[[str], None] = lambda _phrase: None,
        search_again: Callable[[], None] = lambda: None,
        toggle_mute: Callable[[], None] = lambda: None,
        set_volume: Callable[[int], None] = lambda _percent: None,
        previous_track: Callable[[], None] = lambda: None,
        toggle_playback: Callable[[], None] = lambda: None,
        stop_playback: Callable[[], None] = lambda: None,
        next_track: Callable[[], None] = lambda: None,
        toggle_view: Callable[[], None] = lambda: None,
        toggle_cover_size: Callable[[], None] = lambda: None,
        open_equaliser: Callable[[], None] = lambda: None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("Tray")
        # A container is never a stop, so it is said rather than assumed.
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.choose_button = _icon_button(
            self,
            resources.choose_folder_icon_path(),
            "Choose music folder",
            choose_folder,
        )
        self.rescan_button = _icon_button(
            self, resources.rescan_icon_path(), "Rescan the library", rescan
        )
        self.repair_button = _icon_button(
            self, resources.library_health_icon_path(), REPAIR_TOOLTIP, repair_library
        )
        # Nothing to press yet: what each issue should become is worked out on
        # every load; there is nowhere to keep a correction once accepted.
        self.repair_button.setEnabled(False)
        self.search_button = _icon_button(
            self, resources.search_icon_path(), "Search the library", toggle_search
        )
        self.search_box = QLineEdit(self)
        self.search_box.setObjectName("SearchBox")
        self.search_box.setPlaceholderText(SEARCH_PLACEHOLDER)
        self.search_box.setFixedSize(SEARCH_BOX_PX, SEARCH_BOX_HEIGHT_PX)
        # Hidden until asked for, so the tray is pictures until it is not.
        self.search_box.setVisible(False)
        self.search_box.textChanged.connect(search_changed)
        # Return asks the same phrase again, which is the only way back to
        # what it found for somebody who has since moved off it.
        self.search_box.returnPressed.connect(search_again)
        self.showing = ShowingControls(
            self,
            BUTTON_PX,
            ICON_PX,
            TRAY_GAP_PX,
            toggle_view=toggle_view,
            toggle_cover_size=toggle_cover_size,
            open_equaliser=open_equaliser,
        )
        self.previous_button = _icon_button(
            self, resources.previous_icon_path(), "Previous track", previous_track
        )
        self.play_button = _icon_button(
            self, resources.play_icon_path(), "Play", toggle_playback
        )
        self.stop_button = _icon_button(
            self, resources.stop_icon_path(), "Stop", stop_playback
        )
        self.next_button = _icon_button(
            self, resources.next_icon_path(), "Next track", next_track
        )
        self.volume_button = _icon_button(
            self, resources.volume_icon_path(), "Volume", self._open
        )
        self._popup = VolumeSlider(self, set_volume)
        self._percent = DEFAULT_PERCENT
        self.mute_button = _icon_button(
            self, resources.unmute_icon_path(), "Mute", toggle_mute
        )
        self.separator = separator(self, SEPARATOR_WIDTH_PX, SEPARATOR_HEIGHT_PX)
        self.theme_button = _icon_button(self, None, "", toggle_theme)
        self.help_button = _icon_button(
            self, resources.info_icon_path(), HELP_TOOLTIP, self._open_help
        )
        self.help_menu = QMenu(self)
        self.help_menu.addAction(ABOUT_ENTRY, show_about)
        self.help_menu.addAction(UPDATES_ENTRY, check_for_updates)
        row = QHBoxLayout(self)
        row.setContentsMargins(
            TRAY_MARGIN_PX, TRAY_MARGIN_PX, TRAY_MARGIN_PX, TRAY_MARGIN_PX
        )
        row.setSpacing(TRAY_GAP_PX)
        row.addWidget(self.choose_button)
        row.addWidget(self.rescan_button)
        row.addWidget(self.repair_button)
        row.addWidget(self.search_button)
        row.addWidget(self.search_box)
        row.addWidget(self.showing)
        # A stretch either side is what centres the transport, whatever the
        # window is widened to and whatever sits at the two ends.
        row.addStretch()
        for button in self.transport_stops():
            row.addWidget(button)
        row.addStretch()
        row.addWidget(self.volume_button)
        row.addWidget(self.mute_button)
        row.addWidget(self.separator)
        row.addWidget(self.theme_button)
        row.addWidget(self.help_button)

    def transport_stops(self) -> tuple[QPushButton, ...]:
        """The transport, left to right: previous, play, stop, next."""
        return (
            self.previous_button,
            self.play_button,
            self.stop_button,
            self.next_button,
        )

    def ring_stops(self) -> tuple[QWidget, ...]:
        """This tray's controls, left to right as they are drawn.

        The repair control is named here while it is disabled, so the ring
        picks it up on the day it works without the order being revisited. Qt
        skips a disabled stop, so naming it costs nothing until then. The
        search box is named for the same reason while it is hidden, since Qt
        skips an invisible stop too.
        """
        return (
            self.choose_button,
            self.rescan_button,
            self.repair_button,
            self.search_button,
            self.search_box,
            *self.showing.stops(),
            *self.transport_stops(),
            self.volume_button,
            self.mute_button,
            self.theme_button,
            self.help_button,
        )

    def set_showing_covers(self, covers: bool) -> None:
        """Say what pressing the view toggle would do from here."""
        self.showing.set_showing_covers(covers)

    def set_next_cover_size(self, size: CoverSize) -> None:
        """Show the size a press would move to, tooltip included."""
        self.showing.set_next_cover_size(size)

    @property
    def searching(self) -> bool:
        """True while the box is open, whatever has been typed into it.

        Asked of the box rather than of the screen. `isVisible` is false while
        the window itself is hidden. Stellody spends time in the notification
        area, so a toggle reading it would stop working exactly there.
        """
        return not self.search_box.isHidden()

    def set_searching(self, searching: bool) -> None:
        """Open the box and put the caret in it, else close it and forget it.

        Closing clears the phrase rather than merely hiding it. A box that is
        out of sight while still narrowing the library is a library that looks
        as though it has lost albums.
        """
        if not searching:
            self.search_box.clear()
        self.search_box.setVisible(searching)
        if searching:
            self.search_box.setFocus(Qt.FocusReason.TabFocusReason)

    def set_playing(self, playing: bool) -> None:
        """Show the action the button would take, not the state it is in.

        A button showing what pressing it does is the same way round as the
        appearance toggle, which shows the appearance it would switch to.
        """
        path = resources.pause_icon_path() if playing else resources.play_icon_path()
        if path is not None:
            self.play_button.setIcon(QIcon(str(path)))
        self.play_button.setToolTip("Pause" if playing else "Play")

    def set_transport_enabled(
        self, loaded: bool, playing: bool, can_start: bool
    ) -> None:
        """Offer only what can actually be done right now.

        Play is offered whenever there is something to start, which includes a
        track merely selected in the library: a play button that does nothing
        until a track has already been started by other means is a play button
        that is never the way anybody starts one.
        """
        for button in (self.previous_button, self.next_button):
            button.setEnabled(loaded)
        self.play_button.setEnabled(loaded or can_start)
        self.stop_button.setEnabled(playing)

    def set_percent(self, percent: int) -> None:
        """Remember where the volume is, so the slider opens showing it."""
        self._percent = percent
        self.volume_button.setToolTip(f"Volume {percent}%")

    def _open(self) -> None:
        """Put the slider up; take it down when it is already up."""
        if self._popup.isVisible():
            self._popup.hide()
            return
        if self._popup.dismissed_by(self.volume_button):
            return
        self._popup.open_at(self._percent, self.volume_button)

    def _open_help(self) -> None:
        """Drop the help menu under its button; take it down when it is up.

        Under rather than over; aligned to the button's left edge, so it
        opens where the button is rather than wherever the pointer happens to
        be. A second press closes it, which is how the volume popup behaves.
        """
        if self.help_menu.isVisible():
            self.help_menu.hide()
            return
        corner = self.help_button.rect().bottomLeft()
        self.help_menu.popup(self.help_button.mapToGlobal(corner))

    def set_muted(self, muted: bool) -> None:
        """Show what a press would do, as every button in this tray does.

        A struck speaker while the sound is on says a press silences it; a
        plain one while it is off says a press brings it back. It showed the
        state instead, which read as inverted beside the view toggle and the
        appearance toggle: both of those name where a press would take you,
        so a picture of where you already are is read the wrong way round.

        The tooltip says the same thing in words, so the two agree rather
        than each carrying half of it.
        """
        speaker = resources.unmute_icon_path()
        self.mute_button.setIcon(
            plain_icon(speaker)
            if muted
            else struck_through(speaker, resources.negative_icon_path(), ICON_PX)
        )
        self.mute_button.setToolTip("Unmute" if muted else "Mute")

    def set_mode(self, mode: Mode) -> None:
        """Show the appearance the toggle would switch TO, as the installer does."""
        arriving = Mode.LIGHT if mode is Mode.DARK else Mode.DARK
        path = (
            resources.light_mode_icon_path()
            if arriving is Mode.LIGHT
            else resources.dark_mode_icon_path()
        )
        if path is not None:
            self.theme_button.setIcon(QIcon(str(path)))
        self.theme_button.setToolTip(f"Switch to the {arriving.value} appearance")
