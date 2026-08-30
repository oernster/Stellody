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

That toggle names what pressing it will do rather than which view is on
show, since a button that reads as a label is read as a state and pressed to
confirm it.

Shuffle and repeat show their STATE by being lit rather than by being struck
through. The slash means one thing across the application, that what the
picture depicts is not happening, which is true of a silenced speaker and is
the wrong reading for a switch that is merely off: a row where the same mark
meant "engaged" on one button and "not engaged" on the next was read exactly
as the contradiction it was. Their tooltips name the action, so the pair still
says both things at once.

The slider is a popup rather than a permanent bar, so an application that is
mostly a library does not spend a strip of window on something touched twice a
session.
"""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QPoint, QSize, Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

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

# The slider runs in whole percent, which is what the label says and what is
# stored. The engine takes a fraction, so one conversion lives at that seam.
MINIMUM_PERCENT = 0
MAXIMUM_PERCENT = 100
# Where the volume starts when nothing has been chosen yet. Full is loud
# enough to be startling on a first run; three quarters leaves room to go up.
DEFAULT_PERCENT = 75
PERCENT_STEP = 5
SLIDER_HEIGHT_PX = 220
SLIDER_MARGIN_PX = 10

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
    makes this a control rather than a second window to manage. That same rule
    is what makes the button hard to close it with, so where the closing press
    landed is kept: see mousePressEvent below.
    """

    def __init__(self, parent: QWidget, on_change: Callable[[int], None]) -> None:
        super().__init__(parent, Qt.WindowType.Popup)
        self.setObjectName("VolumePopup")
        # Where the press that closed this last landed, in screen coordinates.
        self._dismissed_over: QPoint | None = None
        self.slider = QSlider(Qt.Orientation.Vertical, self)
        self.slider.setObjectName("Volume")
        self.slider.setRange(MINIMUM_PERCENT, MAXIMUM_PERCENT)
        self.slider.setValue(DEFAULT_PERCENT)
        self.slider.setSingleStep(PERCENT_STEP)
        self.slider.setPageStep(PERCENT_STEP * HALF)
        self.slider.setFixedHeight(SLIDER_HEIGHT_PX)
        self.slider.valueChanged.connect(on_change)
        column = QVBoxLayout(self)
        column.setContentsMargins(
            SLIDER_MARGIN_PX, SLIDER_MARGIN_PX, SLIDER_MARGIN_PX, SLIDER_MARGIN_PX
        )
        # Above the slider, where the eye lands first on a column that is read
        # top down; also where the handle never covers it at full volume.
        self.reading = QLabel(self)
        self.reading.setObjectName("VolumeReading")
        self.reading.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        column.addWidget(self.reading, alignment=Qt.AlignmentFlag.AlignHCenter)
        column.addWidget(self.slider, alignment=Qt.AlignmentFlag.AlignHCenter)
        self.slider.valueChanged.connect(self._show_percent)
        self._show_percent(self.slider.value())

    def _show_percent(self, percent: int) -> None:
        """Say the level in the whole percent the tooltip and the store use.

        A slider on its own says roughly; a number says which. They are the
        same value read two ways, so the number is driven by the slider rather
        than set beside it; the two cannot disagree.
        """
        self.reading.setText(f"{percent}%")

    def open_at(self, percent: int, button: QWidget) -> None:
        """Show the slider above its button, set to where the volume is."""
        self._dismissed_over = None
        self.slider.setValue(percent)
        corner = button.mapToGlobal(button.rect().topLeft())
        self.move(
            corner.x() + (button.width() - self.sizeHint().width()) // HALF,
            corner.y() - self.sizeHint().height(),
        )
        self.show()
        self.slider.setFocus(Qt.FocusReason.PopupFocusReason)

    def mousePressEvent(self, event) -> None:
        """Close on a press outside, remembering where that press landed.

        Windows replays the press that dismisses a popup to whatever sits
        under the cursor, so a press on the button that opened this closed it
        and then immediately reopened it: measured as a slider that would not
        go away, intermittently, since the replay is what decides it.

        Keeping the position lets the button tell that replayed click apart
        from a fresh one. Windows is the only platform built today; on one
        that does not replay, the record is read by the next press instead,
        which then puts the slider up on the press after it.
        """
        inside = self.rect().contains(event.position().toPoint())
        self._dismissed_over = None if inside else event.globalPosition().toPoint()
        super().mousePressEvent(event)

    def dismissed_by(self, button: QWidget) -> bool:
        """Whether the press that closed this landed on that button.

        Reading forgets, so one press is answered once and never twice.
        """
        where = self._dismissed_over
        self._dismissed_over = None
        if where is None:
            return False
        return button.rect().contains(button.mapFromGlobal(where))


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
        on_change: Callable[[int], None],
        toggle_shuffle: Callable[[], None] = lambda: None,
        toggle_repeat: Callable[[], None] = lambda: None,
        toggle_view: Callable[[], None] = lambda: None,
        toggle_cover_size: Callable[[], None] = lambda: None,
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
        self.shuffle_button = _switch_button(self, "Turn shuffle on", toggle_shuffle)
        self.repeat_button = _switch_button(self, "Turn repeat on", toggle_repeat)
        self.view_button = _small_button(
            self, resources.view_icon_path(), COVERS_TOOLTIP, toggle_view
        )
        # Named for the size it would move to, like the view toggle beside it:
        # a button naming what is already on show reads as a label.
        self.size_button = _small_button(self, None, "", toggle_cover_size)
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
        row.addWidget(self.size_button)
        row.addWidget(self.repair_button)
        # The stretch splits the strip. What changes the library sits under
        # the library; the settings finish at the right edge under the
        # application's other controls.
        row.addStretch()
        for button in self.switch_stops():
            row.addWidget(button)
        self._percent = DEFAULT_PERCENT
        self.set_shuffled(False)
        self.set_repeating(False)

    def ring_stops(self) -> tuple[QPushButton, ...]:
        """This tray's controls, left to right as they are drawn.

        The repair control is named here while it is disabled, so the ring
        picks it up on the day it works without the order being revisited. Qt
        skips a disabled stop, so naming it costs nothing until then.
        """
        return (
            self.donate_button,
            self.view_button,
            self.size_button,
            self.repair_button,
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
        """Light one switch while it is on; say what a press would do.

        The picture is the same either way. What changes is the button behind
        it, which the stylesheet fills while it is checked, so the state is
        carried by the control rather than by an alteration to the artwork.
        """
        button.setIcon(plain_icon(path))
        button.setChecked(on)
        button.setToolTip(f"Turn {name} {'off' if on else 'on'}")

    def _open(self) -> None:
        """Put the slider up; take it down when it is already up."""
        if self._popup.isVisible():
            self._popup.hide()
            return
        if self._popup.dismissed_by(self.volume_button):
            return
        self._popup.open_at(self._percent, self.volume_button)
