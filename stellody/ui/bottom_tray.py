"""The strip along the bottom: shuffle and repeat, the view and the sleeves.

Its own strip rather than a place in the tray above, because none of these is
a transport command. They are settings that outlast the track in hand; they
belong where a setting sits. Three quarters of the size of the tray above it,
derived from that tray's own sizes so the two cannot drift apart: subordinate
to the tray without the artwork becoming too small to read.

The volume is the exception; it sits in the tray above beside the mute
switch. The two are one thought: how loud, then whether at all. Splitting them
across two strips meant crossing the window to do half of it.

The switches sit at the right end, under About and the appearance toggle,
which is where the application's own controls already are. The view toggle
sits at the left instead, under the library it would change rather than among
the settings, with the donate button outside it at the very end of the row:
it belongs to nothing on screen, so it sits where nothing else is reached
by accident.

That toggle names what pressing it will do rather than which view is on
show, since a button that reads as a label is read as a state and pressed to
confirm it.

Shuffle and repeat show their STATE by being lit rather than by being struck
through, which is where this strip parts from the tray above: that one acts,
so its pictures say what a press would do; this one holds settings, so its
switches say how things stand. A cross here would be read as the mark the tray
uses and taken for an action, on a control that is not offering one. Their
tooltips name the action, so the pair still says both things at once.
"""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QHBoxLayout, QPushButton, QWidget

from stellody.domain.playback import RepeatMode
from stellody.shared import resources
from stellody.ui.covering import CoverSize
from stellody.ui.icons import plain_icon
from stellody.ui.toolbar import BUTTON_PX, ICON_PX, TRAY_GAP_PX, TRAY_MARGIN_PX

HALF = 2
# Three quarters of the tray above. Expressed against that tray's own sizes so
# the two cannot drift apart when either is retuned.
SWITCH_NUMERATOR = 3
SWITCH_DENOMINATOR = 4
BOTTOM_BUTTON_PX = BUTTON_PX * SWITCH_NUMERATOR // SWITCH_DENOMINATOR
BOTTOM_ICON_PX = ICON_PX * SWITCH_NUMERATOR // SWITCH_DENOMINATOR
BOTTOM_MARGIN_PX = TRAY_MARGIN_PX // HALF


# Said plainly, because the button is on screen before the feature behind it.
# Nothing reads album art off disk or off a music database yet.
COVERS_TOOLTIP = "Switch to album art"
LIST_TOOLTIP = "Switch to the list"
# One picture per size, named against the size itself rather than by position,
# so adding a fourth size cannot silently shift the other three.
SIZE_ICONS = {
    CoverSize.MEDIUM: resources.medium_grid_icon_path,
    CoverSize.LARGE: resources.large_grid_icon_path,
    CoverSize.EXTRA_LARGE: resources.extra_large_grid_icon_path,
}
SIZE_NAMES = {
    CoverSize.MEDIUM: "medium",
    CoverSize.LARGE: "large",
    CoverSize.EXTRA_LARGE: "extra large",
}
# Shuffle says its state with the fill alone, which is all two states need.
# Three cannot be told apart that way, so each repeat state carries its own
# picture and the fill is left saying only that something is on.
REPEAT_ICONS = {
    RepeatMode.OFF: resources.repeat_icon_path,
    RepeatMode.ALBUM: resources.repeat_album_icon_path,
    RepeatMode.ONE: resources.repeat_one_icon_path,
}
# Named for what the next press does, which is the rule the other tooltips on
# this strip follow.
REPEAT_TIPS = {
    RepeatMode.OFF: "Repeat the album",
    RepeatMode.ALBUM: "Repeat one track",
    RepeatMode.ONE: "Turn repeat off",
}
# The same honesty as the view toggle. What the health report lists can be
# worked out, since resolution already happens on load; nothing yet lets a
# correction be accepted and kept, so there is nothing for this to do.
# Said in the tooltip because pressing it leaves the application, which a
# picture of a beer and a coffee does not on its own tell anybody.
DONATE_TOOLTIP = "Buy the author a drink (opens your browser)"


def _small_button(
    parent: QWidget, path, tip: str, on_click: Callable[[], None]
) -> QPushButton:
    """One picture button, matching the tray above at three quarters scale."""
    button = QPushButton(parent)
    button.setObjectName("TrayButton")
    button.setToolTip(tip)
    button.setFixedSize(BOTTOM_BUTTON_PX, BOTTOM_BUTTON_PX)
    button.setIconSize(QSize(BOTTOM_ICON_PX, BOTTOM_ICON_PX))
    if path is not None:
        button.setIcon(QIcon(str(path)))
    button.clicked.connect(on_click)
    return button


def _switch_button(
    parent: QWidget, tip: str, on_click: Callable[[], None]
) -> QPushButton:
    """One picture button that stays down while whatever it names is on.

    Checkable rather than repainted, so the lit state is the button's own and
    a reader of the widget is told which of them are engaged.
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
        toggle_view: Callable[[], None] = lambda: None,
        toggle_cover_size: Callable[[], None] = lambda: None,
        open_donation: Callable[[], None] = lambda: None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("BottomTray")
        # A container is never a stop, so it is said rather than assumed.
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.shuffle_button = _switch_button(self, "Turn shuffle on", toggle_shuffle)
        self.repeat_button = _switch_button(self, "Turn repeat on", toggle_repeat)
        self.view_button = _small_button(
            self, resources.view_icon_path(), COVERS_TOOLTIP, toggle_view
        )
        # Named for the size it would move to, like the view toggle beside it:
        # a button naming what is already on show reads as a label.
        self.size_button = _small_button(self, None, "", toggle_cover_size)
        self.donate_button = _small_button(
            self, resources.donate_icon_path(), DONATE_TOOLTIP, open_donation
        )
        row = QHBoxLayout(self)
        row.setContentsMargins(
            BOTTOM_MARGIN_PX, BOTTOM_MARGIN_PX, BOTTOM_MARGIN_PX, BOTTOM_MARGIN_PX
        )
        row.setSpacing(TRAY_GAP_PX)
        row.addWidget(self.donate_button)
        row.addWidget(self.view_button)
        row.addWidget(self.size_button)
        # The stretch splits the strip. What changes the library sits under
        # the library; the settings finish at the right edge under the
        # application's other controls.
        row.addStretch()
        for button in self.switch_stops():
            row.addWidget(button)
        self.set_shuffled(False)
        self.set_repeat(RepeatMode.OFF)

    def ring_stops(self) -> tuple[QPushButton, ...]:
        """This tray's controls, left to right as they are drawn.

        The size button is named here while it is dead over the list, so the
        ring picks it up in the grid without the order being revisited. Qt
        skips a disabled stop, so naming it costs nothing while it is one.
        """
        return (
            self.donate_button,
            self.view_button,
            self.size_button,
            *self.switch_stops(),
        )

    def set_showing_covers(self, covers: bool) -> None:
        """Say what pressing the view toggle would do from here.

        The size button means nothing over the list, so it is disabled there
        rather than left to do nothing: a dead stop is skipped by the ring and
        shows no border, which is how this application says not now.
        """
        self.view_button.setToolTip(LIST_TOOLTIP if covers else COVERS_TOOLTIP)
        self.size_button.setEnabled(covers)

    def set_next_cover_size(self, size: CoverSize) -> None:
        """Show the size a press would move to; say it in the tooltip too."""
        self.size_button.setIcon(plain_icon(SIZE_ICONS[size]()))
        self.size_button.setToolTip(f"Show {SIZE_NAMES[size]} album art")

    def switch_stops(self) -> tuple[QPushButton, ...]:
        """The settings at the right end, left to right as they are drawn."""
        return (self.shuffle_button, self.repeat_button)

    def set_shuffled(self, shuffled: bool) -> None:
        """Strike the shuffle switch through while the album plays in order."""
        self._show_switch(
            self.shuffle_button, resources.shuffle_icon_path(), shuffled, "shuffle"
        )

    def set_repeat(self, repeat: RepeatMode) -> None:
        """Show which of the three repeat states the switch is holding."""
        self.repeat_button.setIcon(plain_icon(REPEAT_ICONS[repeat]()))
        self.repeat_button.setChecked(repeat.repeats)
        self.repeat_button.setToolTip(REPEAT_TIPS[repeat])

    def _show_switch(self, button: QPushButton, path, on: bool, name: str) -> None:
        """Light one switch while it is on; say what a press would do.

        The picture is the same either way. What changes is the button behind
        it, which the stylesheet fills while it is checked, so the state is
        carried by the control rather than by an alteration to the artwork.
        """
        button.setIcon(plain_icon(path))
        button.setChecked(on)
        button.setToolTip(f"Turn {name} {'off' if on else 'on'}")
