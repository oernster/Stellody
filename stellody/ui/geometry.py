"""Remembering how big the window was left.

Its own module rather than another method on the window, for the same reason
the scanning and the playing are: over there is what the window IS, here is one
concern about it, kept whole. The window module was also within twenty lines of
the length a module is allowed here, so a fortieth method was not going in it.

Two things are stored, not one. A window left MAXIMISED reports the screen as
its size, so storing that alone would come back as a window the size of the
screen that is not actually maximised: the same shape with none of the
behaviour; no way back to the size it had before either. The size kept is
therefore the one it would return to, with the maximised state beside it.

A run with nothing written down opens MAXIMISED. Ruled on 2026-09-07: a
freshly installed copy has no remembered size, so it opened at a default that
somebody then had to maximise before doing anything with a library. It applies
to the first run alone, since every run after it has a choice to honour: a
window deliberately left at half the screen comes back at half the screen.

A fresh install, a repair and a reinstall open the same way on the screen setup
was on, ruled on 2026-09-13. Setup leaves a note naming that screen; the
composition root forgets the size on reading it, then `open_on` lays the window
in that screen's room before it is shown. An update leaves no note, so a size
left at the last run still comes back.

What comes back is checked rather than trusted. A size is clamped to the screen
now attached, because a window sized for a monitor that is no longer there
opens with its controls past the edge. That clamp is necessary and not
sufficient, which `fit_on_screen` below is the second half of. It is clamped to
what the window says it needs too, since a stored size smaller than that is one
nobody can use. A value that is not a number at all falls back to the size a
first run opens at, which is the same fallback the volume and the cover size
already use.
"""

from __future__ import annotations

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QGuiApplication

from stellody.ui.maximising import screen_at
from stellody.ui.settings_keys import (
    FALSE,
    SETTING_WINDOW_HEIGHT,
    SETTING_WINDOW_MAXIMISED,
    SETTING_WINDOW_WIDTH,
    TRUE,
)

# What remembering the window writes down; forgetting it clears the same three.
WINDOW_KEYS = (SETTING_WINDOW_WIDTH, SETTING_WINDOW_HEIGHT, SETTING_WINDOW_MAXIMISED)
# How a key nobody has stated reads, so a forgotten one reads the same way.
UNSTATED = ""


def forget_window(settings) -> None:
    """Forget the size the window was left at, so the next one opens maximised.

    What setup asks for after a fresh install, a repair or a reinstall.
    """
    for key in WINDOW_KEYS:
        settings.set_setting(key, UNSTATED)


def screen_named(name: str, origin: tuple[int, int] | None, screens):
    """The screen setup named: by its corner, else by its name; None if neither.

    The corner first, since on Windows Qt places every screen at its native
    origin; a name is the fallback for a screen whose corner has moved.
    """
    screens = tuple(screens)
    if origin is not None:
        found = screen_at(origin, screens)
        if found is not None:
            return found
    return next((screen for screen in screens if name and screen.name() == name), None)


class Geometry:
    """The window's half of remembering the size it was left at."""

    def restore_geometry(self, default: QSize) -> None:
        """Open at the size last left; maximised where nothing was left.

        The size is set either way, since it is the one to come back to when
        the window is restored down from maximised.
        """
        wanted = QSize(
            self._stored_length(SETTING_WINDOW_WIDTH, default.width()),
            self._stored_length(SETTING_WINDOW_HEIGHT, default.height()),
        )
        self.resize(self._usable(wanted))
        if self._first_run() or self._flag(SETTING_WINDOW_MAXIMISED):
            # Set rather than shown: this runs while the window is still
            # being built; showMaximized here would put it on screen early.
            self.setWindowState(self.windowState() | Qt.WindowState.WindowMaximized)

    def _first_run(self) -> bool:
        """Whether any earlier run wrote down a size to come back to.

        All three keys are asked rather than one, so a settings file half
        written by an older version is read as remembering something rather
        than as a fresh install to be maximised over the top of.
        """
        return not any(self._settings.get_setting(key, UNSTATED) for key in WINDOW_KEYS)

    def open_on(self, name: str, origin: tuple[int, int] | None) -> bool:
        """Lay the window in the room of the screen setup was on, maximised there.

        Called before the window is shown. Measured on the real platform on
        2026-09-13 across four monitors of mixed scaling: laid in a screen's
        room first, then marked maximised, the window landed maximised on that
        screen every time. False where no attached screen answers to the note,
        which leaves the window wherever Qt put it.
        """
        target = screen_named(name, origin, self._screens())
        if target is None:
            return False
        room = target.availableGeometry()
        maximised = Qt.WindowState.WindowMaximized
        self.setWindowState(self.windowState() & ~maximised)
        self.resize(self.size().boundedTo(room.size()))
        self.move(room.topLeft())
        self.setWindowState(self.windowState() | maximised)
        return True

    def _screens(self):
        """Every attached screen; its own method so a test can stand some in."""
        return QGuiApplication.screens()

    def fit_on_screen(self) -> None:
        """Maximise where the content restored to will not fit the screen.

        `resize` sets the CONTENT size while `availableGeometry` measures room
        for a whole window, its frame included, so a size restored at the width
        of the screen asks for a window wider than the screen. Windows charges
        eight pixels a side for a resize border it never draws and reports none
        of that through `frameMargins`, measured on this machine: 3440 of
        content on a 3440 wide screen came back as a 3456 wide window whose
        content started eight pixels in, putting its last eight columns off the
        monitor. What that cost was the focus ring of the right-most control,
        which sits six pixels inside that edge, on a window nobody could see
        was not maximised.

        So the guard is stated on what Qt does report correctly, which is where
        the content actually landed. Maximised rather than nudged aside: a nudge
        would need the same frame width that cannot be read, while a window
        filling the screen is one somebody had maximised in every case that
        reaches here.
        """
        if self.isMaximized():
            return
        screen = self._usable_screen()
        if screen is None:
            return
        if not screen.availableGeometry().contains(self.geometry()):
            self.showMaximized()

    def remember_geometry(self) -> None:
        """Write down the size to come back to, with the maximised state.

        Called on the way out by every door, since the cross can leave the
        application running in the notification area and the tray's Quit then
        closes a window that was already hidden.
        """
        maximised = self.isMaximized()
        size = self.normalGeometry().size() if maximised else self.size()
        if size.isEmpty():
            size = self.size()
        self._settings.set_setting(SETTING_WINDOW_WIDTH, str(size.width()))
        self._settings.set_setting(SETTING_WINDOW_HEIGHT, str(size.height()))
        self._settings.set_setting(
            SETTING_WINDOW_MAXIMISED, TRUE if maximised else FALSE
        )

    def _usable_screen(self):
        """The screen a restored size has to fit on; None when there is none.

        Its own method so a test can stand in front of it: the offscreen
        platform reports an 800 by 800 screen, which would clamp every size
        asked for and hide whether the restore happened at all.
        """
        return self.screen() or QGuiApplication.primaryScreen()

    def _stored_length(self, key: str, fallback: int) -> int:
        """One stored measurement; the fallback when it is not a number."""
        try:
            return int(self._settings.get_setting(key, ""))
        except ValueError:
            return fallback

    def _usable(self, wanted: QSize) -> QSize:
        """A size that fits the screen now attached and is big enough to use.

        The screen asked is the one this window is on rather than the primary
        one, since a second monitor is often the larger of the two and clamping
        to the primary would shrink a window that fitted perfectly well.

        The ceiling here is room for a WINDOW while the size returned is its
        CONTENT, so a size at the ceiling still overhangs by whatever the frame
        costs. That difference cannot be read before the window exists, so it
        is answered afterwards in `fit_on_screen` rather than guessed at here.
        """
        floor = self.minimumSizeHint()
        screen = self._usable_screen()
        ceiling = screen.availableGeometry().size() if screen is not None else wanted
        return QSize(
            min(max(wanted.width(), floor.width()), ceiling.width()),
            min(max(wanted.height(), floor.height()), ceiling.height()),
        )
