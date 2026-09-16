"""The icon tray under the menus.

Picture-only buttons in reading order: choose the music folder, narrow it to a
genre and search it on the left, the transport centred, then discovery, the
appearance toggle and Help on the right. The library buttons
repeat something the menus already offer, so they add reach rather than
capability; nothing here owns any state of its own.

Filter sits between choosing and searching, which is where it belongs on both
counts. The search button and the box it opens are one control in two pieces,
so nothing may come between them; a filter is a question about the library in
the same way choosing a folder is. It opens a dialog rather than narrowing
on the press, since what to show has to be said before it can be shown.

Search is the one place a box joins the pictures. The button carries the
magnifier and the box appears beside it only while searching, so the tray
reads as pictures until somebody asks it not to. Filtering happens as the box
is typed into, which is why the button opens the box rather than running
anything: there would be nothing for a second press to do.

Rescan and repair are not here. They are errands about what the library holds
rather than about what is playing, so they sit on the bottom strip among the
things that outlast a track. The volume, mute and the equalizer sit there too,
beside shuffle and repeat, as settings a listener leaves somewhere.

Discovery is ruled off from the two buttons after it. It acts on the library
while they act on the application, so a line says they are different kinds of
thing rather than leaving the three to read as one group.

Every picture here says what a press would DO rather than what is the case:
the appearance toggle shows the appearance it would move to.

The transport is centred because it is the one group that is about the track
rather than about the library; also because a play button in the corner of a
window is a play button nobody finds.

The tray itself is a container, so it never takes focus and never paints a ring.
Its buttons are controls and wear the app's three ring states.
"""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QLineEdit, QMenu, QPushButton, QWidget

from stellody.shared import resources
from stellody.ui.discovery_progress import DiscoveryBars
from stellody.ui.theme import Mode
from stellody.ui.tray_metrics import (
    BUTTON_PX,
    DISCOVER_TOOLTIP,
    FILTER_TOOLTIP,
    FILTERED_TOOLTIP,
    HELP_TOOLTIP,
    SEARCH_BOX_HEIGHT_PX,
    SEARCH_BOX_PX,
    SEARCH_PLACEHOLDER,
    SEPARATOR_HEIGHT_PX,
    SEPARATOR_WIDTH_PX,
    TRAY_GAP_PX,
    TRAY_MARGIN_PX,
    tray_button,
)
from stellody.ui.tray_parts import centred_row, group, separator


class LibraryTray(QWidget):
    """The strip of icon buttons that sits between the menus and the library."""

    def __init__(
        self,
        parent: QWidget,
        choose_folder: Callable[[], None],
        toggle_theme: Callable[[], None],
        help_menu: QMenu,
        open_filter: Callable[[], None] = lambda: None,
        open_discovery: Callable[[], None] = lambda: None,
        toggle_search: Callable[[], None] = lambda: None,
        search_changed: Callable[[str], None] = lambda _phrase: None,
        search_again: Callable[[], None] = lambda: None,
        previous_track: Callable[[], None] = lambda: None,
        toggle_playback: Callable[[], None] = lambda: None,
        stop_playback: Callable[[], None] = lambda: None,
        next_track: Callable[[], None] = lambda: None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("Tray")
        # Without this the stylesheet's border-bottom is dropped in
        # silence. See BottomTray for the measurement.
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        # A container is never a stop, so it is said rather than assumed.
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.choose_button = tray_button(
            self,
            resources.choose_folder_icon_path(),
            "Choose music folder",
            choose_folder,
        )
        self.filter_button = tray_button(
            self, resources.filter_icon_path(), FILTER_TOOLTIP, open_filter
        )
        # Checkable so a filter that is on can hold the button down. The
        # artwork says what the control is; the pressed look says whether it
        # is currently doing anything, which a narrowed library cannot say
        # for itself: it looks exactly like a small one.
        self.filter_button.setCheckable(True)
        self.search_button = tray_button(
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
        self.previous_button = tray_button(
            self, resources.previous_icon_path(), "Previous track", previous_track
        )
        self.play_button = tray_button(
            self, resources.play_icon_path(), "Play", toggle_playback
        )
        self.stop_button = tray_button(
            self, resources.stop_icon_path(), "Stop", stop_playback
        )
        self.next_button = tray_button(
            self, resources.next_icon_path(), "Next track", next_track
        )
        # The run reports here rather than in a dialog, so the dialog can shut
        # the moment it has been told what to look for. Reserved rather than
        # shown only while a run is under way: appearing would move every
        # button beside it and shift the centred transport with them.
        #
        # Two bars in the height one used to take, one for each half of a run.
        # The name is unchanged, since what the window has to say to it is
        # unchanged: here is a report, draw it.
        self.discovery_bar = DiscoveryBars(self, BUTTON_PX)
        self.discover_button = tray_button(
            self,
            resources.discover_icon_path(),
            DISCOVER_TOOLTIP,
            open_discovery,
        )
        # Discovery is a library action; theme and help act on the application.
        # A line goes between the two to keep that boundary visible.
        self.library_separator = separator(
            self, SEPARATOR_WIDTH_PX, SEPARATOR_HEIGHT_PX
        )
        self.theme_button = tray_button(self, None, "", toggle_theme)
        self.help_button = tray_button(
            self, resources.info_icon_path(), HELP_TOOLTIP, self._open_help
        )
        # The menu bar's own Help menu rather than one built alike, so the
        # button cannot come to offer less than the menu or word it otherwise.
        self.help_menu = help_menu
        # The transport at the middle of the tray rather than the middle of
        # what the two ends leave over: see centred_row for why those differ.
        centred_row(
            self,
            TRAY_MARGIN_PX,
            TRAY_GAP_PX,
            group(
                TRAY_GAP_PX,
                self.choose_button,
                self.filter_button,
                self.search_button,
                self.search_box,
            ),
            group(TRAY_GAP_PX, *self.transport_stops()),
            group(
                TRAY_GAP_PX,
                self.discovery_bar,
                self.discover_button,
                self.library_separator,
                self.theme_button,
                self.help_button,
            ),
        )

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

        The search box is named here while it is hidden, so the ring picks it
        up the moment it opens without the order being revisited. Qt skips an
        invisible stop, so naming it costs nothing while it is one.
        """
        return (
            self.choose_button,
            self.filter_button,
            self.search_button,
            self.search_box,
            *self.transport_stops(),
            self.discover_button,
            self.theme_button,
            self.help_button,
        )

    @property
    def searching(self) -> bool:
        """True while the box is open, whatever has been typed into it.

        Asked of the box rather than of the screen. `isVisible` is false while
        the window itself is hidden. Stellody spends time in the notification
        area, so a toggle reading it would stop working exactly there.
        """
        return not self.search_box.isHidden()

    def set_filtering(self, filtering: bool, what: str) -> None:
        """Hold the filter button down while it is narrowing the library.

        The tooltip names what is being asked for rather than repeating the
        control's own name, so the state can be read without opening the
        dialog to look at the ticks.
        """
        self.filter_button.setChecked(filtering)
        self.filter_button.setToolTip(
            FILTERED_TOOLTIP.format(what=what) if filtering else FILTER_TOOLTIP
        )

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
