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

from PySide6.QtCore import QTimer, Slot
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
        self._picture_page = self._library.addWidget(self._picture_surface)
        self._picture_showing = False
        self._page_left = 0
        self._picture_timer = QTimer(self)
        self._picture_timer.setInterval(PICTURE_TICK_MS)
        self._picture_timer.timeout.connect(self._tick_picture)

    @property
    def picture_surface(self) -> QWidget:
        """The surface itself, for a window that needs to place or read it."""
        return self._picture_surface

    def follow_picture(self) -> None:
        """Open or give up the picture as the track in hand changes.

        Called from the transport poll, so it is asked of every track, most of
        which have no picture at all. Whether anything has changed is decided
        below rather than by the caller.
        """
        if self._pictures is None:
            return
        playing = self._transport.current
        self._pictures.follow(playing.source if playing is not None else None)
        if self._pictures.showing and not self._picture_showing:
            self._take_the_library_area()
        elif not self._pictures.showing and self._picture_showing:
            self._give_the_library_area_back()

    def _take_the_library_area(self) -> None:
        """Remember where the listener was, then show the picture there."""
        self._picture_showing = True
        self._page_left = self._library.currentIndex()
        self._library.setCurrentIndex(self._picture_page)
        self._picture_timer.start()
        self._tick_picture()

    def _give_the_library_area_back(self) -> None:
        """Put the listener back on the view they were on, as they left it.

        The page is restored rather than chosen: a grid put back this way is
        still scrolled to the sleeve it was scrolled to, which is the whole
        point of taking the area rather than opening a window over it.
        """
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
