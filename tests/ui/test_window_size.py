"""The window opens at the size it was left at.

Two values are stored rather than one. A window left MAXIMISED reports the
screen as its size, so keeping that alone would come back as a window the size
of the screen that is not actually maximised, with no way back to the size it
had before. What is kept is the size it would return to, with the maximised
state beside it.

What comes back is checked rather than trusted: clamped to the screen now
attached, floored at what the window says it needs, then falling back to the
size a first run opens at when the stored value is not a number.
"""

from __future__ import annotations

import pytest
from conftest import RecordingPlayer
from PySide6.QtCore import QRect, Qt
from tray_support import RememberingStore, build

from stellody.ui.geometry import Geometry
from stellody.ui.main_window import WINDOW_HEIGHT_PX, WINDOW_WIDTH_PX
from stellody.ui.settings_keys import (
    FALSE,
    SETTING_WINDOW_HEIGHT,
    SETTING_WINDOW_MAXIMISED,
    SETTING_WINDOW_WIDTH,
    TRUE,
)

ROOMY_WIDTH_PX = 2560
ROOMY_HEIGHT_PX = 1440
# Narrower than the window those two describe, so its content overhangs.
CRAMPED_WIDTH_PX = 1800


class RoomyScreen:
    """A screen larger than the offscreen platform's, so nothing is clamped.

    Stood in front of the real one because that platform reports 800 by 800:
    every size asked for would come back clamped and the restore itself would
    never be seen to happen.
    """

    def availableGeometry(self) -> QRect:
        """Room for any size these tests ask for."""
        return QRect(0, 0, ROOMY_WIDTH_PX, ROOMY_HEIGHT_PX)


@pytest.fixture
def roomy(monkeypatch: pytest.MonkeyPatch):
    """Every window built in this module sees the roomier screen."""
    monkeypatch.setattr(Geometry, "_usable_screen", lambda self: RoomyScreen())


def window(store: RememberingStore):
    """A real window over a store that remembers."""
    return build(store, RecordingPlayer(), leave=lambda: None)


class TestWhatIsWrittenDown:
    def test_a_first_run_opens_at_the_default(self, application, roomy) -> None:
        made = window(RememberingStore())
        assert made.size().width() == WINDOW_WIDTH_PX
        assert made.size().height() == WINDOW_HEIGHT_PX
        made.close()

    def test_closing_writes_the_size_down(self, application, roomy) -> None:
        store = RememberingStore()
        made = window(store)
        made.show()
        made.resize(1600, 910)
        made.close()
        assert store.settings[SETTING_WINDOW_WIDTH] == "1600"
        assert store.settings[SETTING_WINDOW_HEIGHT] == "910"
        assert store.settings[SETTING_WINDOW_MAXIMISED] == FALSE

    def test_the_next_run_opens_at_that_size(self, application, roomy) -> None:
        store = RememberingStore(
            {SETTING_WINDOW_WIDTH: "1600", SETTING_WINDOW_HEIGHT: "910"}
        )
        made = window(store)
        assert made.size().width() == 1600
        assert made.size().height() == 910
        made.close()

    def test_the_default_is_never_narrower_than_the_window_needs(
        self, application, roomy
    ) -> None:
        """Every control in the trays is a fixed size, so they set the floor.

        The default is chosen for the library rather than for the strips, so
        nothing keeps the two in step by itself. A default below the floor
        opens the window with a control cut off its own strip.
        """
        made = window(RememberingStore())
        assert WINDOW_WIDTH_PX >= made.minimumSizeHint().width()
        assert WINDOW_HEIGHT_PX >= made.minimumSizeHint().height()
        made.close()


class TestLeftMaximised:
    def test_the_size_to_come_back_to_is_what_is_kept(self, application, roomy) -> None:
        """Not the screen it filled, which is no size to reopen at."""
        store = RememberingStore()
        made = window(store)
        made.show()
        made.resize(1520, 800)
        made.showMaximized()
        made.close()
        assert store.settings[SETTING_WINDOW_MAXIMISED] == TRUE
        assert store.settings[SETTING_WINDOW_WIDTH] == "1520"
        assert store.settings[SETTING_WINDOW_HEIGHT] == "800"

    def test_it_comes_back_maximised(self, application, roomy) -> None:
        store = RememberingStore(
            {
                SETTING_WINDOW_MAXIMISED: TRUE,
                SETTING_WINDOW_WIDTH: "1520",
                SETTING_WINDOW_HEIGHT: "800",
            }
        )
        made = window(store)
        assert made.windowState() & Qt.WindowState.WindowMaximized
        made.close()

    def test_a_window_left_ordinary_comes_back_ordinary(
        self, application, roomy
    ) -> None:
        store = RememberingStore({SETTING_WINDOW_MAXIMISED: FALSE})
        made = window(store)
        assert not made.windowState() & Qt.WindowState.WindowMaximized
        made.close()


class TestASizeThatCannotBeUsed:
    def test_something_that_is_not_a_number_falls_back(
        self, application, roomy
    ) -> None:
        store = RememberingStore(
            {SETTING_WINDOW_WIDTH: "wide", SETTING_WINDOW_HEIGHT: ""}
        )
        made = window(store)
        assert made.size().width() == WINDOW_WIDTH_PX
        assert made.size().height() == WINDOW_HEIGHT_PX
        made.close()

    def test_a_size_smaller_than_the_window_needs_is_floored(
        self, application, roomy
    ) -> None:
        store = RememberingStore(
            {SETTING_WINDOW_WIDTH: "10", SETTING_WINDOW_HEIGHT: "12"}
        )
        made = window(store)
        assert made.size().width() == made.minimumSizeHint().width()
        assert made.size().height() == made.minimumSizeHint().height()
        made.close()

    def test_a_size_bigger_than_the_screen_is_clamped(self, application, roomy) -> None:
        """A window sized for a monitor no longer there opens past the edge."""
        store = RememberingStore(
            {SETTING_WINDOW_WIDTH: "99999", SETTING_WINDOW_HEIGHT: "99999"}
        )
        made = window(store)
        assert made.size().width() == ROOMY_WIDTH_PX
        assert made.size().height() == ROOMY_HEIGHT_PX
        made.close()

    def test_no_screen_at_all_leaves_the_size_asked_for(
        self, application, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Nothing to clamp against is not a reason to refuse a size."""
        monkeypatch.setattr(Geometry, "_usable_screen", lambda self: None)
        store = RememberingStore(
            {SETTING_WINDOW_WIDTH: "1600", SETTING_WINDOW_HEIGHT: "910"}
        )
        made = window(store)
        assert made.size().width() == 1600
        assert made.size().height() == 910
        made.close()


class CrampedScreen:
    """A screen the restored content is deliberately too wide for.

    The real fault cannot be reached offscreen at all, since that platform
    draws no window frame: what put the content past the edge on Windows was
    eight pixels a side of resize border that Qt reports as nothing. So the
    overhang is stated here instead, by giving the window a screen it does not
    fit on, which is the same condition `fit_on_screen` answers.
    """

    def availableGeometry(self) -> QRect:
        """Narrower than the window this module builds."""
        return QRect(0, 0, CRAMPED_WIDTH_PX, ROOMY_HEIGHT_PX)


class TestContentThatWouldSitPastTheEdge:
    def test_a_window_wider_than_its_screen_opens_maximised(
        self, application, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The measured fault: content as wide as the screen overhangs it.

        A window restored at the width of the monitor is not maximised, so its
        frame is added OUTSIDE the size asked for and the content lands past
        the edge, taking the right-most control's focus ring with it.
        """
        monkeypatch.setattr(Geometry, "_usable_screen", lambda self: RoomyScreen())
        store = RememberingStore(
            {
                SETTING_WINDOW_WIDTH: str(ROOMY_WIDTH_PX),
                SETTING_WINDOW_HEIGHT: str(ROOMY_HEIGHT_PX),
            }
        )
        made = window(store)
        monkeypatch.setattr(Geometry, "_usable_screen", lambda self: CrampedScreen())
        made.show()
        application.processEvents()
        assert made.isMaximized()
        made.close()

    def test_a_window_that_fits_is_left_exactly_as_it_was(
        self, application, roomy
    ) -> None:
        """The guard answers an overhang; it has no opinion about anything else."""
        store = RememberingStore(
            {SETTING_WINDOW_WIDTH: "1600", SETTING_WINDOW_HEIGHT: "910"}
        )
        made = window(store)
        made.show()
        application.processEvents()
        assert not made.isMaximized()
        assert made.size().width() == 1600
        made.close()
