"""The window's half of showing a picture: taking the area, then giving it back.

The picture takes the library's own area rather than a window of its own, so a
video track is the same gesture as any other track: it plays where the library
was and closing it puts the listener back exactly where they were, with the
grid still scrolled to the sleeve they came from. A second window would make a
bonus video a different kind of thing from the song beside it on the same disc.

Two clocks, deliberately. The transport poll is a quarter of a second, which is
right for a position bar and far too slow for a picture; the tick here runs at
the rate the pictures themselves were made at. It runs only while something is
showing, so a library of songs pays nothing for it.

The tick never decides what should be showing. It asks where the sound has
reached and hands that moment on; the sound is the clock, so the two streams
cannot drift apart because only one of them is keeping time.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, QTimer, Slot
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import QWidget

from stellody.application.pictures import Pictures
from stellody.ui.picture_view import PictureSurface

# Every video in the reference library was made at 25 pictures a second, so a
# tick of 40 milliseconds asks exactly as often as a frame can change. Asking
# faster would decode nothing new; asking slower would show one frame twice.
PICTURE_TICK_MS = 40


class Picturing:
    """Shows the picture of the track in hand where the library was."""

    def start_picturing(self, pictures: Pictures | None) -> None:
        """Build the surface, add it to the library's holder and stand ready.

        A window given no service shows no picture, which is the shape every
        other optional service here has: a test about something else builds a
        window without one and is never asked to supply a decoder.
        """
        self._pictures = pictures
        self._picture_surface = PictureSurface(self)
        self._picture_surface.size_toggled.connect(self.toggle_picture_size)
        self._picture_page = self._library.addWidget(self._picture_surface)
        self._picture_showing = False
        self._picture_filling = False
        self._page_left = 0
        self._picture_timer = QTimer(self)
        self._picture_timer.setInterval(PICTURE_TICK_MS)
        self._picture_timer.timeout.connect(self._tick_picture)
        # Escape is the way out of anything that has taken the window over, so
        # it is the way out of this. It answers only while the picture is
        # filling the window, leaving the key to whatever else wants it.
        self._picture_escape = QShortcut(QKeySequence(Qt.Key.Key_Escape), self)
        self._picture_escape.activated.connect(self.shrink_picture)
        self._picture_escape.setEnabled(False)

    @property
    def picture_fills_window(self) -> bool:
        """True while the picture has the whole window rather than the library."""
        return self._picture_filling

    @Slot()
    def toggle_picture_size(self) -> None:
        """The one press: fill the window, else put it back."""
        if self._picture_filling:
            self.shrink_picture()
        else:
            self.fill_window_with_picture()

    def fill_window_with_picture(self) -> None:
        """Give the picture the whole window, hiding what surrounds it.

        Only what is around the library goes: the toolbar above, the position
        bar and the strip below, plus the menu and the status line. The library
        holder itself stays, since the picture is one of its pages, so nothing
        is rebuilt and putting it back is a matter of showing them again.
        """
        if self._picture_filling or not self._picture_showing:
            return
        self._picture_filling = True
        for part in self._picture_surroundings():
            part.setVisible(False)
        self._picture_surface.set_filling(True)
        self._picture_escape.setEnabled(True)

    def shrink_picture(self) -> None:
        """Put the picture back to the library's own area."""
        if not self._picture_filling:
            return
        self._picture_filling = False
        for part in self._picture_surroundings():
            part.setVisible(True)
        self._picture_surface.set_filling(False)
        self._picture_escape.setEnabled(False)

    def _picture_surroundings(self) -> tuple[QWidget, ...]:
        """Everything that shares the window with the library."""
        return (
            self._tray,
            self._position_bar,
            self._bottom_tray,
            self.menuBar(),
            self.statusBar(),
        )

    @property
    def picture_surface(self) -> QWidget:
        """The surface itself, for a window that needs to place or read it."""
        return self._picture_surface

    def follow_picture(self) -> None:
        """Open or give up the picture as the track in hand changes.

        Called from the transport poll, so it is asked of every track, most of
        which have no picture at all. Whether anything has changed is decided
        below rather than by the caller.

        A track waiting unplayed at its beginning shows nothing, whatever it
        holds. Back lands there, so stepping back through a run of videos was
        leaving the library area taken by a first frame nobody had asked to
        see: these files open on black and fade in over about a second, so the
        window went black and stayed black. A listener who has not started a
        track is still looking for one; the library is what they are
        looking through. Pausing part way through is the other case entirely
        and keeps its picture, since that track has been started.
        """
        if self._pictures is None:
            return
        playing = self._transport.current
        if playing is None or self._transport.waiting_at_the_start:
            self._pictures.follow(None)
        else:
            self._pictures.follow(playing.source)
        if self._pictures.showing and not self._picture_showing:
            self._take_the_library_area()
        elif not self._pictures.showing and self._picture_showing:
            self._give_the_library_area_back()

    def _take_the_library_area(self) -> None:
        """Remember where the listener was, then show the picture there."""
        self._picture_showing = True
        self._page_left = self._library.currentIndex()
        self._library.setCurrentIndex(self._picture_page)
        self._picture_surface.set_filling(False)
        self._picture_timer.start()
        self._tick_picture()

    def _give_the_library_area_back(self) -> None:
        """Put the listener back on the view they were on, as they left it.

        The page is restored rather than chosen: a grid put back this way is
        still scrolled to the sleeve it was scrolled to, which is the whole
        point of taking the area rather than opening a window over it.
        """
        # Put the window back before the page, so a track ending while the
        # picture filled it never leaves a library with no toolbar around it.
        self.shrink_picture()
        self._picture_showing = False
        self._picture_timer.stop()
        self._picture_surface.clear()
        self._library.setCurrentIndex(self._page_left)

    @Slot()
    def _tick_picture(self) -> None:
        """Draw whatever is showing at the moment the sound has reached."""
        position = self._transport.position
        if position is None or self._pictures is None:
            return
        picture = self._pictures.at(position.elapsed_ms)
        if picture is None:
            return
        self._picture_surface.show_picture(picture)

    def stop_picturing(self) -> None:
        """Give up the file and the tick, on the way out of the application."""
        self._picture_timer.stop()
        if self._pictures is not None:
            self._pictures.close()
