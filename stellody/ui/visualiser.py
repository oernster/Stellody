"""The display that moves with the music: two bars to each equalizer band.

Drawn rather than assembled out of widgets, for the reason the stars are:
twenty progress bars would be twenty things for the toolkit to lay out and
repaint thirty times a second, where this is one paint of twenty rectangles.
It is a
display and never a control, so it takes no focus and wears no ring.

**It runs on its own clock, faster than the music reports.** A block carries
about 93 milliseconds of audio, so measurements land some eleven times a
second, which is slow enough to see as steps. The strip repaints far more
often than that and lets `domain/spectrum.py` decide where a bar has fallen to
in between, so what is on screen moves continuously while every peak in it was
really measured.

**Nothing runs while nothing is playing.** The timer is stopped whenever the
music is, with the measurement upstream stopped too, so a window sitting idle
does no arithmetic at all. Stopping also clears the bars: a display frozen mid
height after the music stops looks like one that has crashed rather than one
that is waiting.

It sits in the middle of the bottom strip rather than in a band of its own.
It is a small thing that moves, not a feature that wants a sixth of the window:
the room it was given as its own strip was room taken from the library, which
is what a listener actually looks at.

Its width is stated in centimetres and worked out from the screen it is on,
so it stays the size it was asked to be wherever it is opened rather than
shrinking on one display and sprawling on another. Its height is the tray's
own, handed in, so the two cannot drift apart.

**It draws in one of ten named styles**, chosen from a list lifted up over a
button on the strip and listed in `visualisations.py`: the plain bars in the
accent, the rest in colours of their own. This widget runs the clock and keeps
the heights; how a frame looks is the painters' (`spectrum_styles.py` names
them), so a style changes nothing about what is measured. Heights are
fractions of the strip and colours come from the palette, so nothing here knows
a pixel count or a colour value that the palette or the layout does not already
own.

**It has a ground of its own, plus a baseline it draws even in silence.** It had
neither at first, which measured as a strip of exactly one colour, the window's:
turned on with nothing playing it was indistinguishable from empty space, so a
listener switching it on saw nothing happen and concluded it was not there. It
now wears the surface both trays wear and each band keeps a low mark on
the floor. Silence then reads as twenty bars
with nothing in them rather than as an absence.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QPainter, QPaintEvent
from PySide6.QtWidgets import QWidget

from stellody.domain.spectrum import SILENT_BANDS, fallen, held
from stellody.ui.palette import Mode, palette_for
from stellody.ui.spectrum_styles import PAINTERS
from stellody.ui.visualisations import DEFAULT_VISUALISATION, Visualisation

# Thirty a second. Fast enough that a falling bar reads as movement rather than
# as a slideshow, slow enough that the strip is not the reason a laptop's fan
# comes on: each frame is twenty rectangles.
FRAME_MS = 33
# How wide it should be on the desk, rather than on a particular screen. Turned
# into pixels against the display it opens on, so the same request means the
# same thing on a laptop panel and on a large monitor.
STRIP_WIDTH_CM = 5.0
MILLIMETRES_PER_INCH = 25.4
MILLIMETRES_PER_CM = 10.0
STRIP_HEIGHT_PX = 64
STRIP_MARGIN_PX = 3
_MILLISECONDS = 1000.0


class Visualiser(QWidget):
    """Twenty bands showing how loud each half of each band is, in one style."""

    def __init__(
        self, parent: QWidget | None = None, height_px: int = STRIP_HEIGHT_PX
    ) -> None:
        super().__init__(parent)
        self.setObjectName("Visualiser")
        # A display, never a stop: it holds no value and answers no key.
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setFixedSize(self._asked_width(), height_px)
        self._mode = Mode.DARK
        self._style = DEFAULT_VISUALISATION
        self._shown = SILENT_BANDS
        self._peaks = SILENT_BANDS
        self._reading = SILENT_BANDS
        # Answers silence until something is wired up, so a strip started
        # before it has a source draws empty rather than raising.
        self._source = lambda: SILENT_BANDS
        self._timer = QTimer(self)
        self._timer.setInterval(FRAME_MS)
        self._timer.timeout.connect(self._tick)

    def _asked_width(self) -> int:
        """The stated width in centimetres, in this screen's own pixels.

        Asked of the widget rather than written down, so a display that reports
        a different resolution gets a strip of the same real size rather than
        the same number of pixels.
        """
        per_millimetre = self.logicalDpiX() / MILLIMETRES_PER_INCH
        return round(STRIP_WIDTH_CM * MILLIMETRES_PER_CM * per_millimetre)

    @property
    def running(self) -> bool:
        """True while the strip is repainting itself."""
        return self._timer.isActive()

    @property
    def shown(self) -> tuple[float, ...]:
        """Where the bars have reached, which is what a paint would draw."""
        return self._shown

    @property
    def peaks(self) -> tuple[float, ...]:
        """Where each band's peak mark hangs, which the meter and wave draw."""
        return self._peaks

    @property
    def style(self) -> Visualisation:
        """Which of the visualisations a paint draws."""
        return self._style

    def show_style(self, style: Visualisation) -> None:
        """Draw the same bands another way from the next paint on."""
        self._style = style
        self.update()

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
        self._peaks = SILENT_BANDS
        self._reading = SILENT_BANDS
        self.update()

    def show_appearance(self, mode: Mode) -> None:
        """Draw in the appearance the rest of the window is wearing."""
        self._mode = mode
        self.update()

    def _tick(self) -> None:
        """One frame: take whatever has been measured, let the bars fall to it."""
        seconds = FRAME_MS / _MILLISECONDS
        self._reading = self._source()
        self._shown = fallen(self._shown, self._reading, seconds)
        # Kept whichever style is on show, so switching to one that draws the
        # peaks shows where they really are rather than starting them at zero.
        self._peaks = held(self._peaks, self._shown, seconds)
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        """The ground, then the bands drawn the way the chosen style draws them."""
        palette = palette_for(self._mode)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        # The ground the trays wear, so the strip is visibly a strip whether or
        # not there is anything in it. It draws no rule of its own: it sits
        # inside the bottom tray now, so the tray's own edges are what rule it
        # off and a second line here floated across the middle of the row.
        painter.fillRect(self.rect(), QColor(palette.surface))
        # The bands are laid out across the room that is left rather than at a
        # width of their own, so widening the display or dividing the bands
        # again changes nothing here.
        inner = self.rect().adjusted(
            STRIP_MARGIN_PX, STRIP_MARGIN_PX, -STRIP_MARGIN_PX, -STRIP_MARGIN_PX
        )
        PAINTERS[self._style](painter, inner, self._shown, self._peaks, palette)
        painter.end()
