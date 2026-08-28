"""Gentle auto-scroll for long content: it reads itself, then yields at once.

A surface holds still when it opens, reads down slowly, holds at the end so the
tail can be finished, rewinds fast and starts again. Any reading by hand only
SUSPENDS the cycle: after a moment of stillness it picks up from wherever the
reader stopped, so taking over never switches the feature off for the rest of
the surface's life.

The pace is the same on every surface. The constants belong to this class and
never to a dialog, because a surface that needs its own pace means the pace is
wrong everywhere.

Two corrections are folded in, both of them learned the hard way elsewhere:

- A dialog that focuses its own text as it opens must not read as a reader
  taking hold; the long opening stillness would silently become the short
  manual one. Focus arrivals are ignored until the opening hold is spent; the
  flag clears the moment that hold runs out rather than on the first movement,
  so a reader arriving in between is not missed.
- A surface frozen under a modal must ignore INPUT as well as time. A closing
  dialog returns its view to the top; acting on that would leave the surface
  suspended instead of exactly where it was. A frozen surface has no
  reader by definition, so nothing reaching it can be one.
"""

from __future__ import annotations

from PySide6.QtCore import QEvent, QObject, QTimer
from PySide6.QtWidgets import QApplication, QWidget

TICK_MS = 40
DOWN_STEP_PX = 1
DOWN_TICKS_PER_STEP = 2
UP_STEP_PX = 15
START_PAUSE_MS = 5000
BOTTOM_PAUSE_MS = 5000
TOP_PAUSE_MS = 2000
RESUME_AFTER_MS = 2500


class AutoScroller(QObject):
    """Cycles a scrollable widget: down slowly, hold, rewind fast, repeat.

    Works on any surface exposing verticalScrollBar() and viewport(). The
    widget becomes the scroller's Qt parent, so their lifetimes match.
    """

    DOWN = "down"
    UP = "up"
    PAUSE_TOP = "pause_top"
    PAUSE_BOTTOM = "pause_bottom"
    MANUAL = "manual"
    _WAITING = (PAUSE_TOP, PAUSE_BOTTOM, MANUAL)
    _MANUAL_EVENTS = (
        QEvent.Type.Wheel,
        QEvent.Type.MouseButtonPress,
        QEvent.Type.KeyPress,
    )

    def __init__(self, area) -> None:
        super().__init__(area)
        self._area = area
        self._bar = area.verticalScrollBar()
        self._down_countdown = DOWN_TICKS_PER_STEP
        # Open holding still, then the first descent begins. The overflow
        # guard in the tick means the wait only counts down once there is
        # something to scroll.
        self._phase = self.PAUSE_TOP
        self._wait_ms = START_PAUSE_MS
        self._opening = True
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.timer.start(TICK_MS)
        # The viewport sees the wheel and the clicks; the widget sees the keys.
        area.installEventFilter(self)
        area.viewport().installEventFilter(self)
        self._bar.sliderPressed.connect(self.suspend)
        self._bar.sliderReleased.connect(self.suspend)
        self._bar.sliderMoved.connect(self._on_slider_moved)
        # A child never sees the surface's own filter, so keyboard navigation
        # into one is watched at the application instead.
        application = QApplication.instance()
        if application is not None:
            application.focusChanged.connect(self._on_focus_changed)

    @property
    def phase(self) -> str:
        """Where in the cycle the surface currently is."""
        return self._phase

    def suspend(self) -> None:
        """Hand the content over and start counting down to resume.

        Gated on the freeze rather than each watcher, so a modal closing over
        this surface cannot corrupt the phase the freeze exists to preserve.
        """
        if self.frozen():
            return
        self._phase = self.MANUAL
        self._wait_ms = RESUME_AFTER_MS

    def _on_slider_moved(self, _value: int) -> None:
        """Dragging the scrollbar counts as reading by hand."""
        self.suspend()

    def _on_focus_changed(self, _old, new) -> None:
        """Focus reaching the surface is a reader, once the surface is open."""
        if self._opening:
            return
        if isinstance(new, QWidget) and (
            new is self._area or self._area.isAncestorOf(new)
        ):
            self.suspend()

    def eventFilter(self, _obj, event) -> bool:
        """Wheel, click and key on the surface are all reading by hand."""
        if event.type() in self._MANUAL_EVENTS:
            self.suspend()
        return False

    def frozen(self) -> bool:
        """Whether a modal above this surface should freeze the cycle.

        Two surfaces reading at once compete for the eye, so while a modal is
        up only its own surfaces read. Anything beneath freezes in place: no
        wait is consumed, so it resumes exactly where it was.
        """
        modal = QApplication.activeModalWidget()
        if modal is None:
            return False
        return not (modal is self._area.window() or modal.isAncestorOf(self._area))

    def tick(self) -> None:
        """One step of the cycle. Driven by the timer; by a test directly."""
        if self.frozen():
            return
        maximum = self._bar.maximum()
        if maximum <= 0:
            return
        if self._phase in self._WAITING:
            self._wait_ms -= TICK_MS
            if self._wait_ms <= 0:
                # The opening stillness is over, so focus now means a reader.
                self._opening = False
                self._phase = self._resumed_phase(maximum)
            return
        if self._phase == self.DOWN:
            self._descend(maximum)
            return
        self._rewind()

    def _descend(self, maximum: int) -> None:
        """Advance one reading step, holding at the end when it arrives."""
        self._down_countdown -= 1
        if self._down_countdown > 0:
            return
        self._down_countdown = DOWN_TICKS_PER_STEP
        value = self._bar.value() + DOWN_STEP_PX
        if value >= maximum:
            self._bar.setValue(maximum)
            self._phase = self.PAUSE_BOTTOM
            self._wait_ms = BOTTOM_PAUSE_MS
            return
        self._bar.setValue(value)

    def _rewind(self) -> None:
        """Travel back to the top, fast, because this is not a reading pass."""
        value = self._bar.value() - UP_STEP_PX
        if value <= 0:
            self._bar.setValue(0)
            self._phase = self.PAUSE_TOP
            self._wait_ms = TOP_PAUSE_MS
            return
        self._bar.setValue(value)

    def _resumed_phase(self, maximum: int) -> str:
        """The direction to travel once a wait ends.

        After the bottom hold the cycle rewinds. After reading by hand it
        carries on from where the reader stopped, unless they are already at
        the end, where rewinding is the only way on.
        """
        if self._phase == self.PAUSE_BOTTOM:
            return self.UP
        if self._phase == self.MANUAL and self._bar.value() >= maximum:
            return self.UP
        return self.DOWN
