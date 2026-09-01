"""The strip that moves with the music: ten bars, one to each equalizer band.

Drawn rather than assembled out of widgets, for the reason the stars are: ten
progress bars would be ten things for the toolkit to lay out and repaint
thirty times a second, where this is one paint of ten rectangles. It is a
display and never a control, so it takes no focus and wears no ring.

**It runs on its own clock, faster than the music reports.** A block carries
about 93 milliseconds of audio, so measurements land some eleven times a
second, which is slow enough to see as steps. The strip repaints far more
often than that and lets `domain/spectrum.py` decide where a bar has fallen to
in between, so what is on screen moves continuously while every peak in it was
really measured.

**Nothing runs when nothing is watching.** The timer is stopped whenever the
strip is hidden or the music is not playing, with the measurement upstream
switched off too, so a listener who never opens this pays nothing for it.
Stopping also clears the bars: a strip frozen mid-height after the music stops
looks like a display that has crashed rather than one that is idle.

The bars are drawn from the same accent the rest of the application uses, at a
height that is a fraction of the strip, so nothing here knows a pixel count
that the palette or the layout does not already own.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QPainter, QPaintEvent
from PySide6.QtWidgets import QWidget

from stellody.domain.equalising import BAND_COUNT
from stellody.domain.spectrum import EMPTY, SILENT_BANDS, fallen
from stellody.ui.palette import Mode, palette_for

# Thirty a second. Fast enough that a falling bar reads as movement rather than
# as a slideshow, slow enough that the strip is not the reason a laptop's fan
# comes on: each frame is ten rectangles.
FRAME_MS = 33
STRIP_HEIGHT_PX = 64
BAR_GAP_PX = 4
STRIP_MARGIN_PX = 6
BAR_RADIUS_PX = 2
# A bar that has fallen to nothing is drawn as nothing rather than as a sliver,
# so silence looks like silence.
MINIMUM_BAR_PX = 1
_MILLISECONDS = 1000.0


class Visualiser(QWidget):
    """Ten bars showing how loud each band of what is playing is."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("Visualiser")
        # A display, never a stop: it holds no value and answers no key.
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setFixedHeight(STRIP_HEIGHT_PX)
        self._mode = Mode.DARK
        self._shown = SILENT_BANDS
        self._reading = SILENT_BANDS
        # Answers silence until something is wired up, so a strip started
        # before it has a source draws empty rather than raising.
        self._source = lambda: SILENT_BANDS
        self._timer = QTimer(self)
        self._timer.setInterval(FRAME_MS)
        self._timer.timeout.connect(self._tick)

    @property
    def running(self) -> bool:
        """True while the strip is repainting itself."""
        return self._timer.isActive()

    @property
    def shown(self) -> tuple[float, ...]:
        """Where the bars have reached, which is what a paint would draw."""
        return self._shown

    def read_levels_from(self, source) -> None:
        """Say where to fetch a measurement on each frame.

        Pulled rather than pushed. What measures the audio does so on the
        feeder's thread and must never wait for a painter, so it leaves its
        answer where this can come and take it; a strip that cannot keep up
        then misses measurements instead of delaying the music.
        """
        self._source = source

    def start(self) -> None:
        """Begin repainting, unless it is already running."""
        if not self._timer.isActive():
            self._timer.start()

    def stop(self) -> None:
        """Stop repainting and empty the bars."""
        self._timer.stop()
        self._shown = SILENT_BANDS
        self._reading = SILENT_BANDS
        self.update()

    def show_appearance(self, mode: Mode) -> None:
        """Draw in the appearance the rest of the window is wearing."""
        self._mode = mode
        self.update()

    def _tick(self) -> None:
        """One frame: take whatever has been measured, let the bars fall to it."""
        self._reading = self._source()
        self._shown = fallen(self._shown, self._reading, FRAME_MS / _MILLISECONDS)
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        """Ten bars across the strip, each as tall as its band is loud."""
        palette = palette_for(self._mode)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(palette.accent))
        inner = self.rect().adjusted(
            STRIP_MARGIN_PX, STRIP_MARGIN_PX, -STRIP_MARGIN_PX, -STRIP_MARGIN_PX
        )
        span = (inner.width() + BAR_GAP_PX) / BAND_COUNT
        width = max(MINIMUM_BAR_PX, int(span) - BAR_GAP_PX)
        for band, height in enumerate(self._shown):
            if height <= EMPTY:
                continue
            tall = max(MINIMUM_BAR_PX, int(inner.height() * height))
            painter.drawRoundedRect(
                inner.left() + int(band * span),
                inner.bottom() - tall,
                width,
                tall,
                BAR_RADIUS_PX,
                BAR_RADIUS_PX,
            )
        painter.end()
