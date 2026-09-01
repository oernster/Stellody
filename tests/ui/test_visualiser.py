"""The strip: when it runs, when it stops and what it draws while it does.

Time is never waited on. The strip's own frame is driven by calling it, so what
is asserted is the behaviour rather than whatever a sleep happened to catch.

Two questions are kept apart here as they are in the window. Whether the strip
is SHOWN is the listener's and is remembered; whether it is RUNNING is the
music's. A strip on show with nothing playing has nothing to draw; a
measurement taken for a hidden strip is work done for nobody.
"""

from __future__ import annotations

import pytest
from conftest import RecordingPlayer
from PySide6.QtWidgets import QApplication, QMenu
from tray_support import RememberingStore, build

from stellody.domain.equalising import BAND_COUNT
from stellody.domain.playback import PlaybackState
from stellody.domain.spectrum import EMPTY, FULL, SILENT_BANDS
from stellody.ui.bottom_tray import BOTTOM_BUTTON_PX
from stellody.ui.theme import Mode, stylesheet
from stellody.ui.visualiser import (
    MILLIMETRES_PER_CM,
    MILLIMETRES_PER_INCH,
    STRIP_WIDTH_CM,
    Visualiser,
)

LOUD = (FULL,) * BAND_COUNT
# Wide enough that every band gets its own column of pixels to be counted in.
STRIP_WIDTH_PX = 600


@pytest.fixture
def strip(application: QApplication):
    """A strip on its own, with nothing else in the way."""
    made = Visualiser()
    yield made
    made.stop()
    made.close()


class TestTheStripOnItsOwn:
    def test_it_starts_empty_and_still(self, strip) -> None:
        assert strip.shown == SILENT_BANDS
        assert not strip.running

    def test_it_is_never_a_stop(self, strip) -> None:
        """A display holds no value and answers no key, so Tab passes it by."""
        assert int(strip.focusPolicy()) == 0

    def test_a_strip_with_no_source_draws_silence_rather_than_raising(
        self, strip
    ) -> None:
        """Started before it is wired up, which construction order allows."""
        strip.start()
        strip._tick()
        assert strip.shown == SILENT_BANDS

    def test_a_frame_takes_whatever_has_been_measured(self, strip) -> None:
        strip.read_levels_from(lambda: LOUD)
        strip._tick()
        assert strip.shown == LOUD

    def test_bars_fall_between_measurements(self, strip) -> None:
        """The measurement arrives eleven times a second; the strip draws more.

        What is on screen between two measurements is a bar on its way down,
        which is the whole reason the strip has a clock of its own.
        """
        strip.read_levels_from(lambda: LOUD)
        strip._tick()
        strip.read_levels_from(lambda: SILENT_BANDS)
        strip._tick()
        assert all(EMPTY < one < FULL for one in strip.shown), strip.shown

    def test_starting_twice_leaves_one_clock_running(self, strip) -> None:
        strip.start()
        strip.start()
        assert strip.running

    def test_an_idle_strip_still_looks_like_a_strip(
        self, application: QApplication
    ) -> None:
        """Turned on with nothing playing, it must not look like empty space.

        It had no ground of its own at first, which measured as a strip of
        exactly ONE colour: the window's. Switching it on then changed nothing
        anybody could see, which reads as the feature not being there at all.
        Rendering the widget runs its own paintEvent, so what is counted is
        what would be drawn rather than what is on a screen.
        """
        for mode in Mode:
            application.setStyleSheet(stylesheet(mode))
            made = Visualiser()
            made.show_appearance(mode)
            made.resize(STRIP_WIDTH_PX, made.height())
            made.show()
            application.processEvents()
            drawn = made.grab().toImage()
            painted = {
                drawn.pixel(x, y)
                for y in range(0, drawn.height(), 2)
                for x in range(0, drawn.width(), 4)
            }
            assert len(painted) > 1, f"{mode.value}: an idle strip is one flat colour"
            made.close()

    def test_stopping_empties_the_bars(self, strip) -> None:
        """A strip frozen mid-height reads as crashed rather than as idle."""
        strip.read_levels_from(lambda: LOUD)
        strip.start()
        strip._tick()
        strip.stop()
        assert not strip.running
        assert strip.shown == SILENT_BANDS


class TestTheDisplayInTheWindow:
    def window(self, store: RememberingStore, player: RecordingPlayer):
        """A real window over a store that remembers."""
        return build(store, player, leave=lambda: None)

    def test_it_is_simply_there(self, application) -> None:
        """No switch, so nothing to find and nothing to remember."""
        made = self.window(RememberingStore(), RecordingPlayer())
        made.show()
        assert made._visualiser.isVisible()
        assert made._transport.visualising, "measuring from the moment it opens"
        made.close()

    def test_it_lives_in_the_bottom_strip_between_the_two_groups(
        self, application
    ) -> None:
        """A few centimetres of the strip, not a band of the window."""
        made = self.window(RememberingStore(), RecordingPlayer())
        made.show()
        tray = made._bottom_tray
        assert made._visualiser.parent() is tray
        row = tray.layout()
        widgets = [row.itemAt(position).widget() for position in range(row.count())]
        gaps = [position for position, one in enumerate(widgets) if one is None]
        here = widgets.index(made._visualiser)
        assert gaps[0] < here < gaps[1], "a stretch either side is what centres it"
        made.close()

    def test_it_stands_lower_than_the_controls_and_sits_between_them(
        self, application
    ) -> None:
        """Half a button tall, centred against them, derived from their size.

        It is something to notice out of the corner of an eye rather than a
        sixth control, so it should not stand as tall as the things that are;
        the height comes from the tray's own so the two cannot drift apart.
        """
        made = self.window(RememberingStore(), RecordingPlayer())
        made.show()
        strip, tray = made._visualiser, made._bottom_tray
        assert strip.height() == BOTTOM_BUTTON_PX // 2
        centre = strip.mapTo(tray, strip.rect().center()).y()
        assert abs(centre - tray.height() // 2) <= 1, "centred in the strip"
        made.close()

    def test_it_is_the_width_it_was_asked_for_in_centimetres(self, application) -> None:
        """Stated on the desk rather than in pixels, so it travels between screens."""
        made = self.window(RememberingStore(), RecordingPlayer())
        made.show()
        strip = made._visualiser
        per_millimetre = strip.logicalDpiX() / MILLIMETRES_PER_INCH
        wanted = round(STRIP_WIDTH_CM * MILLIMETRES_PER_CM * per_millimetre)
        assert strip.width() == wanted
        made.close()

    def test_the_sound_menu_offers_no_switch_for_it(self, application) -> None:
        """It was a question nobody wanted asked, so it is not asked."""
        made = self.window(RememberingStore(), RecordingPlayer())
        made.show()
        entries = [
            action.text()
            for menu in made.menuBar().findChildren(QMenu)
            if menu.title().replace("&", "") == "Sound"
            for action in menu.actions()
        ]
        assert entries == ["&Equalizer..."]
        made.close()

    def test_it_runs_only_while_something_is_playing(self, application) -> None:
        """Always there is not always working: an idle window draws nothing."""
        player = RecordingPlayer()
        made = self.window(RememberingStore(), player)
        made.show()
        assert not made._visualiser.running, "nothing is playing yet"
        player.state = PlaybackState.PLAYING
        made.follow_spectrum()
        assert made._visualiser.running
        player.state = PlaybackState.STOPPED
        made.follow_spectrum()
        assert not made._visualiser.running
        made.close()
