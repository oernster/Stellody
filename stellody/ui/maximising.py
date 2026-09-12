"""Maximising onto the monitor the title bar is on.

`title_bar` holds the measured fault: Windows maximises onto whichever monitor
holds most of the window, which after a drag between monitors of different
scaling need not be the one its title bar was dropped on. Somebody maximising
a window means the screen they are looking at, which is the one the title bar
they just double clicked is on.

What Windows does by itself is kept wherever it already agrees. A title bar on
the screen Qt already places the window on is left to Windows untouched; only
the case that goes wrong takes the other road.

The other road moves the window onto the title bar's screen at the size it
would restore down to, bounded by that screen's room, then maximises it there.
Moving it first is what makes Windows agree: a window lying on one monitor
takes that monitor's scaling, so the maximise that follows has one place to go.
Measured on the machine it was reported from, with real mouse input: the
window maximised on a 300 percent panel, dragged to the 100 percent screen
above and double clicked. Without this it maximised onto the panel below; with
it, onto the screen above at that screen's own 96 DPI.

Windows names a monitor by its rectangle, so it is matched to Qt's screen by
its top left corner: on Windows Qt places every screen at its native origin
while scaling only the size, measured on all four monitors here. A corner that
matches nothing leaves the maximise to Windows, which is the old behaviour
rather than a new fault.
"""

from __future__ import annotations

import sys
from collections.abc import Iterable
from functools import partial

from PySide6.QtCore import QRect, QTimer
from PySide6.QtGui import QGuiApplication, QScreen

WINDOWS = "win32"

if sys.platform == WINDOWS:
    from stellody.ui import title_bar


def screen_at(origin: tuple[int, int], screens: Iterable[QScreen]) -> QScreen | None:
    """The screen whose top left corner is `origin`; None when there is none."""
    for screen in screens:
        corner = screen.geometry().topLeft()
        if (corner.x(), corner.y()) == origin:
            return screen
    return None


class Maximising:
    """The window's half of maximising where its title bar is."""

    def nativeEvent(self, event_type, message):
        """Take a maximise that Windows would send to a different monitor."""
        if (
            sys.platform == WINDOWS
            and title_bar.is_maximise_command(bytes(event_type), int(message))
            and self.maximise_where_the_title_bar_is()
        ):
            return True, 0
        return super().nativeEvent(event_type, message)

    def maximise_where_the_title_bar_is(self) -> bool:
        """Maximise on the title bar's screen where Windows would not; True if so.

        The command is answered as handled so Windows does not act on it too.
        The move itself waits for the next turn of the event loop rather than
        happening inside the message, which is the form measured working.
        """
        target = self._title_bar_screen()
        if target is None or target is self.screen():
            return False
        QTimer.singleShot(0, partial(self._maximise_within, target.availableGeometry()))
        return True

    def _title_bar_screen(self) -> QScreen | None:
        """The screen the title bar is on; None when that cannot be said.

        Its own method so a test can stand in front of it: the offscreen
        platform has no title bar to ask about.
        """
        origin = title_bar.title_bar_monitor(int(self.winId()))
        if origin is None:
            return None
        return screen_at(origin, QGuiApplication.screens())

    def _maximise_within(self, room: QRect) -> None:
        """Lay the window inside `room` at its restore size, then maximise it.

        The size kept is the one restoring down comes back to, bounded by the
        room, so the window restores to what it was wherever that still fits.
        """
        size = self.normalGeometry().size()
        if size.isEmpty():
            size = self.size()
        self.resize(size.boundedTo(room.size()))
        self.move(room.topLeft())
        self.showMaximized()
