"""The icon tray under the menus.

Picture-only buttons in reading order: choose the music folder and rescan it on
the left, the transport centred, then the appearance toggle and About on the
right. The library buttons repeat something the menus already offer, so they
add reach rather than capability; nothing here owns any state of its own.

The transport is centred because it is the one group that is about the track
rather than about the library; also because a play button in the corner of a
window is a play button nobody finds.

The tray itself is a container, so it never takes focus and never paints a ring.
Its buttons are controls and wear the app's three ring states.
"""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QHBoxLayout, QPushButton, QWidget

from stellody.shared import resources
from stellody.ui.theme import Mode

ICON_PX = 60
BUTTON_PX = 91
TRAY_MARGIN_PX = 6
TRAY_GAP_PX = 6


def _icon_button(parent: QWidget, path, tip: str, on_click: Callable) -> QPushButton:
    """One picture-only button, sized to its artwork."""
    button = QPushButton(parent)
    button.setObjectName("TrayButton")
    button.setToolTip(tip)
    button.setFixedSize(BUTTON_PX, BUTTON_PX)
    button.setIconSize(QSize(ICON_PX, ICON_PX))
    if path is not None:
        button.setIcon(QIcon(str(path)))
    button.clicked.connect(on_click)
    return button


class LibraryTray(QWidget):
    """The strip of icon buttons that sits between the menus and the library."""

    def __init__(
        self,
        parent: QWidget,
        choose_folder: Callable[[], None],
        rescan: Callable[[], None],
        toggle_theme: Callable[[], None],
        show_about: Callable[[], None],
        previous_track: Callable[[], None] = lambda: None,
        toggle_playback: Callable[[], None] = lambda: None,
        stop_playback: Callable[[], None] = lambda: None,
        next_track: Callable[[], None] = lambda: None,
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
        self.theme_button = _icon_button(self, None, "", toggle_theme)
        self.about_button = _icon_button(
            self, resources.info_icon_path(), "About Stellody", show_about
        )
        row = QHBoxLayout(self)
        row.setContentsMargins(
            TRAY_MARGIN_PX, TRAY_MARGIN_PX, TRAY_MARGIN_PX, TRAY_MARGIN_PX
        )
        row.setSpacing(TRAY_GAP_PX)
        row.addWidget(self.choose_button)
        row.addWidget(self.rescan_button)
        # A stretch either side is what centres the transport, whatever the
        # window is widened to and whatever sits at the two ends.
        row.addStretch()
        for button in self.transport_stops():
            row.addWidget(button)
        row.addStretch()
        row.addWidget(self.theme_button)
        row.addWidget(self.about_button)

    def transport_stops(self) -> tuple[QPushButton, ...]:
        """The transport, left to right: previous, play, stop, next."""
        return (
            self.previous_button,
            self.play_button,
            self.stop_button,
            self.next_button,
        )

    def ring_stops(self) -> tuple[QPushButton, ...]:
        """This tray's controls, left to right as they are drawn."""
        return (
            self.choose_button,
            self.rescan_button,
            *self.transport_stops(),
            self.theme_button,
            self.about_button,
        )

    def set_playing(self, playing: bool) -> None:
        """Show the action the button would take, not the state it is in.

        A button showing what pressing it does is the same way round as the
        appearance toggle, which shows the appearance it would switch to.
        """
        path = resources.pause_icon_path() if playing else resources.play_icon_path()
        if path is not None:
            self.play_button.setIcon(QIcon(str(path)))
        self.play_button.setToolTip("Pause" if playing else "Play")

    def set_transport_enabled(self, loaded: bool, playing: bool) -> None:
        """Offer only what can actually be done to what is queued."""
        for button in self.transport_stops():
            button.setEnabled(loaded)
        self.stop_button.setEnabled(playing)

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
