"""The strip along the bottom: volume, shuffle and repeat, plus the slider.

Its own strip rather than a place in the tray above, because none of these is
a transport command. They are settings that outlast the track in hand; they
belong where a setting sits. Three quarters of the size of the tray above it,
derived from that tray's own sizes so the two cannot drift apart: subordinate
to the tray without the artwork becoming too small to read.

The switches sit at the right end, under About and the appearance toggle,
which is where the application's own controls already are. The view toggle
sits at the left instead, under the library it would change rather than among
the settings, with the donate button outside it at the very end of the row:
it belongs to nothing on screen, so it sits where nothing else is reached
by accident.

That toggle is drawn and placed before it does anything. Nothing reads album
art off disk yet, so it is disabled and says so: an offered control that
quietly does nothing is worse than one that plainly cannot be pressed.

Shuffle and repeat show their STATE rather than the action a press would take,
because "off" has no picture of its own: the switch is struck through while it
is off. Their tooltips name the action, so the pair says both things at once.

The slider is a popup rather than a permanent bar, so an application that is
mostly a library does not spend a strip of window on something touched twice a
session.
"""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from stellody.shared import resources
from stellody.ui.icons import plain_icon, struck_through
from stellody.ui.toolbar import BUTTON_PX, ICON_PX, TRAY_GAP_PX, TRAY_MARGIN_PX

HALF = 2
# Three quarters of the tray above. Expressed against that tray's own sizes so
# the two cannot drift apart when either is retuned.
SWITCH_NUMERATOR = 3
SWITCH_DENOMINATOR = 4
BOTTOM_BUTTON_PX = BUTTON_PX * SWITCH_NUMERATOR // SWITCH_DENOMINATOR
BOTTOM_ICON_PX = ICON_PX * SWITCH_NUMERATOR // SWITCH_DENOMINATOR
BOTTOM_MARGIN_PX = TRAY_MARGIN_PX // HALF

# The slider runs in whole percent, which is what the label says and what is
# stored. The engine takes a fraction, so one conversion lives at that seam.
MINIMUM_PERCENT = 0
MAXIMUM_PERCENT = 100
PERCENT_STEP = 5
SLIDER_HEIGHT_PX = 220
SLIDER_MARGIN_PX = 10

# Said plainly, because the button is on screen before the feature behind it.
# Nothing reads album art off disk or off a music database yet.
VIEW_TOOLTIP = "Switch to album art (not built yet)"
# The same honesty as the view toggle. What the health report lists can be
# worked out, since resolution already happens on load; nothing yet lets a
# correction be accepted and kept, so there is nothing for this to do.
REPAIR_TOOLTIP = "Repair what library health reports (not built yet)"
# Said in the tooltip because pressing it leaves the application, which a
# picture of a beer and a coffee does not on its own tell anybody.
DONATE_TOOLTIP = "Buy the author a drink (opens your browser)"


class VolumeSlider(QFrame):
    """A vertical bar with a handle, floating above the button that opened it.

    A popup closes itself when the window is clicked elsewhere, which is what
    makes this a control rather than a second window to manage.
    """

    def __init__(self, parent: QWidget, on_change: Callable[[int], None]) -> None:
        super().__init__(parent, Qt.WindowType.Popup)
        self.setObjectName("VolumePopup")
        self.slider = QSlider(Qt.Orientation.Vertical, self)
        self.slider.setObjectName("Volume")
        self.slider.setRange(MINIMUM_PERCENT, MAXIMUM_PERCENT)
        self.slider.setSingleStep(PERCENT_STEP)
        self.slider.setPageStep(PERCENT_STEP * HALF)
        self.slider.setFixedHeight(SLIDER_HEIGHT_PX)
        self.slider.valueChanged.connect(on_change)
        column = QVBoxLayout(self)
        column.setContentsMargins(
            SLIDER_MARGIN_PX, SLIDER_MARGIN_PX, SLIDER_MARGIN_PX, SLIDER_MARGIN_PX
        )
        column.addWidget(self.slider, alignment=Qt.AlignmentFlag.AlignHCenter)

    def open_at(self, percent: int, button: QWidget) -> None:
        """Show the slider above its button, set to where the volume is."""
        self.slider.setValue(percent)
        corner = button.mapToGlobal(button.rect().topLeft())
        self.move(
            corner.x() + (button.width() - self.sizeHint().width()) // HALF,
            corner.y() - self.sizeHint().height(),
        )
        self.show()
        self.slider.setFocus(Qt.FocusReason.PopupFocusReason)


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


class BottomTray(QWidget):
    """The strip along the bottom, holding the settings that outlast a track."""

    def __init__(
        self,
        parent: QWidget,
        on_change: Callable[[int], None],
        toggle_shuffle: Callable[[], None] = lambda: None,
        toggle_repeat: Callable[[], None] = lambda: None,
        toggle_view: Callable[[], None] = lambda: None,
        open_donation: Callable[[], None] = lambda: None,
        repair_library: Callable[[], None] = lambda: None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("BottomTray")
        # A container is never a stop, so it is said rather than assumed.
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.volume_button = _small_button(
            self, resources.volume_icon_path(), "Volume", self._open
        )
        self.shuffle_button = _small_button(
            self, None, "Turn shuffle on", toggle_shuffle
        )
        self.repeat_button = _small_button(self, None, "Turn repeat on", toggle_repeat)
        self.view_button = _small_button(
            self, resources.view_icon_path(), VIEW_TOOLTIP, toggle_view
        )
        self.view_button.setEnabled(False)
        self.repair_button = _small_button(
            self, resources.library_health_icon_path(), REPAIR_TOOLTIP, repair_library
        )
        self.repair_button.setEnabled(False)
        self.donate_button = _small_button(
            self, resources.donate_icon_path(), DONATE_TOOLTIP, open_donation
        )
        self._popup = VolumeSlider(self, on_change)
        row = QHBoxLayout(self)
        row.setContentsMargins(
            BOTTOM_MARGIN_PX, BOTTOM_MARGIN_PX, BOTTOM_MARGIN_PX, BOTTOM_MARGIN_PX
        )
        row.setSpacing(TRAY_GAP_PX)
        row.addWidget(self.donate_button)
        row.addWidget(self.view_button)
        row.addWidget(self.repair_button)
        # The stretch splits the strip. What changes the library sits under
        # the library; the settings finish at the right edge under the
        # application's other controls.
        row.addStretch()
        for button in self.switch_stops():
            row.addWidget(button)
        self._percent = MAXIMUM_PERCENT
        self.set_shuffled(False)
        self.set_repeating(False)

    def ring_stops(self) -> tuple[QPushButton, ...]:
        """This tray's controls, left to right as they are drawn.

        The view toggle is named here while it is disabled, so the ring picks
        it up on the day it works without the order being revisited. Qt skips
        a disabled stop, so naming it costs nothing until then.
        """
        return (
            self.donate_button,
            self.view_button,
            self.repair_button,
            *self.switch_stops(),
        )

    def switch_stops(self) -> tuple[QPushButton, ...]:
        """The settings at the right end, left to right as they are drawn."""
        return (self.volume_button, self.shuffle_button, self.repeat_button)

    def set_percent(self, percent: int) -> None:
        """Remember where the volume is, so the slider opens showing it."""
        self._percent = percent
        self.volume_button.setToolTip(f"Volume {percent}%")

    def set_shuffled(self, shuffled: bool) -> None:
        """Strike the shuffle switch through while the album plays in order."""
        self._show_switch(
            self.shuffle_button, resources.shuffle_icon_path(), shuffled, "shuffle"
        )

    def set_repeating(self, repeating: bool) -> None:
        """Strike the repeat switch through while the queue ends at its end."""
        self._show_switch(
            self.repeat_button, resources.repeat_icon_path(), repeating, "repeat"
        )

    def _show_switch(self, button: QPushButton, path, on: bool, name: str) -> None:
        """Draw one switch in the state it is in; say what a press would do."""
        button.setIcon(
            plain_icon(path)
            if on
            else struck_through(path, resources.negative_icon_path(), BOTTOM_ICON_PX)
        )
        button.setToolTip(f"Turn {name} {'off' if on else 'on'}")

    def _open(self) -> None:
        """Show the slider where the volume currently stands."""
        self._popup.open_at(self._percent, self.volume_button)
