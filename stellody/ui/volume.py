"""The volume control: a button, with a slider that comes up from it.

A popup rather than a permanent bar, so an application that is mostly a
library does not spend a strip of window on something touched twice a session.

Its own module rather than a part of whichever strip holds the button, so the
button can be moved from one to the other without the slider moving with it.
"""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QFrame, QLabel, QSlider, QVBoxLayout, QWidget

HALF = 2

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


def _screen_top(widget: QWidget) -> int:
    """The top of the screen this widget is on, in screen coordinates.

    The one it is on rather than the primary one, since a window dragged to a
    second screen would otherwise be measured against the wrong edge.
    """
    handle = widget.screen() or QGuiApplication.primaryScreen()
    return handle.availableGeometry().top()


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
        """Show the slider beside its button, set to where the volume is.

        Above the button where there is room for it and below where there is
        not, rather than always above: a button near the top of the screen
        would otherwise put the slider off it. Asked of the screen the button
        is actually on, since a second one may sit above or below the first.
        """
        self._dismissed_over = None
        self.slider.setValue(percent)
        wanted = self.sizeHint()
        top = button.mapToGlobal(button.rect().topLeft())
        bottom = button.mapToGlobal(button.rect().bottomLeft())
        room_above = top.y() - _screen_top(button)
        above = room_above >= wanted.height()
        self.move(
            top.x() + (button.width() - wanted.width()) // HALF,
            top.y() - wanted.height() if above else bottom.y(),
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
