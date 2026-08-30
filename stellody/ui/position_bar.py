"""Where the track has reached, plus a way to move within it.

A plain bar, deliberately. The plan wants position shown as a line crossing the
track's own waveform rather than as a filling bar, which needs the track
decoded ahead of playback and an envelope cached beside the artwork. This is
the stepping stone to that: what it draws is a groove, what it does is the
thing the waveform will also have to do, so the transport wiring, the arithmetic
from a click to a frame and the place in the keyboard order all survive the
change. Only the painting is provisional.

Clicking the groove moves there, rather than nudging a page at a time as Qt
would by default: somebody clicking three quarters of the way along a track
means three quarters of the way along, not one page further on.
"""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QSlider,
    QStyle,
    QStyleOptionSlider,
    QWidget,
)

from stellody.domain.playback import PlaybackPosition, clock_text

# The groove is addressed in thousandths rather than in frames. A frame count
# overruns the range Qt gives a slider on a long track at a high sample rate,
# and a listener cannot aim at a frame anyway.
GROOVE_STEPS = 1000
NO_POSITION_TEXT = "0:00 / 0:00"


class _SeekSlider(QSlider):
    """A slider that goes where it is clicked."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(Qt.Orientation.Horizontal, parent)
        self.setRange(0, GROOVE_STEPS)
        self.setSingleStep(GROOVE_STEPS // 100)
        self.setPageStep(GROOVE_STEPS // 20)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """Jump to the point under the pointer, then let the drag carry on."""
        if event.button() is not Qt.MouseButton.LeftButton:
            super().mousePressEvent(event)
            return
        self.setValue(self._value_under(event))
        self.sliderMoved.emit(self.value())
        super().mousePressEvent(event)

    def _value_under(self, event: QMouseEvent) -> int:
        """The value the pointer is over, allowing for the handle's width."""
        option = QStyleOptionSlider()
        self.initStyleOption(option)
        groove = self.style().subControlRect(
            QStyle.ComplexControl.CC_Slider,
            option,
            QStyle.SubControl.SC_SliderGroove,
            self,
        )
        handle = self.style().subControlRect(
            QStyle.ComplexControl.CC_Slider,
            option,
            QStyle.SubControl.SC_SliderHandle,
            self,
        )
        span = groove.width() - handle.width()
        if span <= 0:
            return self.minimum()
        along = event.position().x() - groove.x() - handle.width() / 2
        return QStyle.sliderValueFromPosition(
            self.minimum(), self.maximum(), int(along), span
        )


class PositionBar(QWidget):
    """The groove, with the time either side of it."""

    def __init__(
        self,
        parent: QWidget | None = None,
        seek: Callable[[int], None] | None = None,
    ) -> None:
        super().__init__(parent)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._seek = seek
        self._frame_count = 0
        self._sample_rate = 0
        self.slider = _SeekSlider(self)
        self.slider.setEnabled(False)
        self.clock = QLabel(NO_POSITION_TEXT, self)
        row = QHBoxLayout(self)
        row.addWidget(self.slider, 1)
        row.addWidget(self.clock)
        self.slider.sliderMoved.connect(self._moved)
        self.slider.sliderReleased.connect(self._released)

    def show_position(self, position: PlaybackPosition | None) -> None:
        """Draw where playback has reached; empty when there is nothing to draw.

        A position arriving while the listener is dragging is ignored. The
        handle belongs to whoever has hold of it; a poll landing mid-drag would
        otherwise drag it back out from under them.
        """
        if position is None:
            self._frame_count = 0
            self.slider.setEnabled(False)
            self.slider.setValue(0)
            self.clock.setText(NO_POSITION_TEXT)
            return
        self._frame_count = position.frame_count
        self._sample_rate = position.sample_rate
        self.slider.setEnabled(position.frame_count > 0)
        if not self.slider.isSliderDown():
            self.slider.setValue(self._steps_for(position.frame))
            self.clock.setText(self._clock_for(position.frame))

    def _steps_for(self, frame: int) -> int:
        """Where along the groove a frame sits."""
        if self._frame_count <= 0:
            return 0
        return min(GROOVE_STEPS, frame * GROOVE_STEPS // self._frame_count)

    def _frame_for(self, steps: int) -> int:
        """The frame a point along the groove stands for."""
        return steps * self._frame_count // GROOVE_STEPS

    def _clock_for(self, frame: int) -> str:
        """The time either side of the groove, at this frame."""
        if self._sample_rate <= 0:
            return NO_POSITION_TEXT
        reached = clock_text(frame, self._sample_rate)
        whole = clock_text(self._frame_count, self._sample_rate)
        return f"{reached} / {whole}"

    def _moved(self, steps: int) -> None:
        """Follow the drag in the clock, without moving the music yet."""
        self.clock.setText(self._clock_for(self._frame_for(steps)))

    def _released(self) -> None:
        """Move the music to where the handle was let go."""
        if self._seek is not None and self._frame_count > 0:
            self._seek(self._frame_for(self.slider.value()))
