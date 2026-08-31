"""Where the track has reached, drawn across the track's own shape.

The amplitude is the point. A groove filling up says how far through a track
playback is; a waveform says that AND what is coming, so the quiet passage
ahead and the moment the piece opens out are both visible before they arrive.

It is a slider underneath, which is deliberate: everything a listener does to
it, clicking anywhere along it, dragging, walking it with the arrow keys, is
behaviour Qt already has right and a control the keyboard ring already knows
about. What is replaced is the painting.

A track whose file has not been measured yet draws a flat line and behaves
exactly as it did before. The shape arrives when the measurement does.
"""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QMouseEvent, QPainter, QPaintEvent
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QSlider,
    QStyle,
    QStyleOptionSlider,
    QWidget,
)

from stellody.domain.listening import NO_STARS, Listening
from stellody.domain.playback import PlaybackPosition, clock_text
from stellody.domain.waveform import Envelope
from stellody.ui.stars import StarRating
from stellody.ui.theme import Mode, palette_for

# The groove is addressed in thousandths rather than in frames. A frame count
# overruns the range Qt gives a slider on a long track at a high sample rate,
# and a listener cannot aim at a frame anyway.
GROOVE_STEPS = 1000
NO_POSITION_TEXT = "0:00 / 0:00"


def _plays_text(record: Listening | None) -> str:
    """How many times this track has played out, said in words.

    Nothing at all until it has played once: a row of tracks each labelled
    with a nought says only that the library is new.
    """
    if record is None or record.plays == 0:
        return ""
    return f"{record.plays} play" + ("" if record.plays == 1 else "s")


# The shape is drawn as one column per pixel, mirrored about the middle.
MINIMUM_COLUMN_HEIGHT = 1.0
PLAYHEAD_WIDTH = 2
# A shape drawn at its measured height would be a thin line for a quiet track
# and full height for a loud one, which says more about mastering than about
# the music. Each track is drawn against its own loudest point instead.
QUIETEST_USEFUL_PEAK = 0.05
FLAT_LINE_HEIGHT = 0.06


class _SeekSlider(QSlider):
    """A slider that goes where it is clicked, drawn as a waveform."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(Qt.Orientation.Horizontal, parent)
        self.setRange(0, GROOVE_STEPS)
        self.setSingleStep(GROOVE_STEPS // 100)
        self.setPageStep(GROOVE_STEPS // 20)
        self._shape: Envelope | None = None
        self._mode = Mode.DARK

    def show_shape(self, shape: Envelope | None) -> None:
        """Draw this shape from now on; a flat line when there is none."""
        self._shape = shape
        self.update()

    def show_appearance(self, mode: Mode) -> None:
        """Follow the appearance the rest of the window is wearing."""
        self._mode = mode
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        """The track's shape, with what has been played marked out in it."""
        palette = palette_for(self._mode)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        middle = self.height() / 2
        played_to = self._played_columns()
        behind = QColor(palette.accent)
        ahead = QColor(palette.text_dim)
        for column, level in enumerate(self._columns()):
            reach = max(MINIMUM_COLUMN_HEIGHT, level * middle)
            painter.fillRect(
                QRectF(column, middle - reach, 1.0, reach * 2),
                behind if column < played_to else ahead,
            )
        painter.fillRect(
            QRectF(played_to, 0.0, PLAYHEAD_WIDTH, float(self.height())),
            QColor(palette.text),
        )
        painter.end()

    def _played_columns(self) -> float:
        """How far along the width the playhead sits."""
        span = self.maximum() - self.minimum()
        if span <= 0:
            return 0.0
        return self.width() * (self.value() - self.minimum()) / span

    def _columns(self) -> tuple[float, ...]:
        """One height per pixel of width, on a scale where 1.0 is full height.

        Drawn against the track's own loudest point rather than against full
        scale, so a quietly mastered record is a shape rather than a smear
        along the middle. A track with nothing in it (or one not yet measured)
        draws a flat line: something has to be there to click on.
        """
        width = max(1, self.width())
        if self._shape is None:
            return (FLAT_LINE_HEIGHT,) * width
        loudest = max(QUIETEST_USEFUL_PEAK, self._shape.loudest)
        return tuple(
            max(FLAT_LINE_HEIGHT, level / loudest)
            for level in self._shape.scaled_to(width)
        )

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
        # The rating rides on this row because this row already follows the
        # same thing it does: what is playing, else what is highlighted. The
        # shape below the line and the stars beside it are two readings of one
        # track, so they belong together rather than at opposite ends.
        self.stars = StarRating(self)
        self.plays = QLabel("", self)
        self.plays.setObjectName("PlayCount")
        row = QHBoxLayout(self)
        row.addWidget(self.slider, 1)
        row.addWidget(self.clock)
        row.addWidget(self.plays)
        row.addWidget(self.stars)
        self.slider.sliderMoved.connect(self._moved)
        self.slider.sliderReleased.connect(self._released)

    def show_shape(self, shape: Envelope | None) -> None:
        """Draw this track's shape; a flat line while there is none."""
        self.slider.show_shape(shape)

    def show_appearance(self, mode: Mode) -> None:
        """Follow the appearance the rest of the window is wearing."""
        self.slider.show_appearance(mode)
        self.stars.show_appearance(mode)

    def show_listening(self, record: Listening | None) -> None:
        """Show one track's rating and count; nothing while there is no track.

        A control that cannot mean anything is disabled rather than left to
        look ready, which is how this application says not now: the ring skips
        it and it paints no border.
        """
        self.stars.setEnabled(record is not None)
        self.stars.show_stars(NO_STARS if record is None else record.stars)
        self.plays.setText(_plays_text(record))

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
