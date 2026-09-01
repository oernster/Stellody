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
from PySide6.QtWidgets import QApplication
from tray_support import RememberingStore, build

from stellody.domain.equalising import BAND_COUNT
from stellody.domain.playback import PlaybackState
from stellody.domain.spectrum import EMPTY, FULL, SILENT_BANDS
from stellody.ui.settings_keys import FALSE, SETTING_VISUALISER, TRUE
from stellody.ui.theme import Mode, stylesheet
from stellody.ui.visualiser import Visualiser

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


class TestTheStripInTheWindow:
    def window(self, store: RememberingStore, player: RecordingPlayer):
        """A real window over a store that remembers."""
        return build(store, player, leave=lambda: None)

    def test_it_is_hidden_until_it_is_asked_for(self, application) -> None:
        """A thing to turn on, so a first run opens on the library."""
        made = self.window(RememberingStore(), RecordingPlayer())
        made.show()
        assert not made._visualiser.isVisible()
        assert not made._transport.visualising
        made.close()

    def test_turning_it_on_shows_it_and_starts_measuring(self, application) -> None:
        """Nothing is measured for nobody, which is what off costing nothing means."""
        made = self.window(RememberingStore(), RecordingPlayer())
        made.show()
        made.toggle_visualiser()
        assert made._visualiser.isVisible()
        assert made._transport.visualising
        made.close()

    def test_turning_it_off_stops_measuring_again(self, application) -> None:
        made = self.window(RememberingStore(), RecordingPlayer())
        made.show()
        made.toggle_visualiser()
        made.toggle_visualiser()
        assert not made._visualiser.isVisible()
        assert not made._transport.visualising
        made.close()

    def test_the_choice_is_written_down(self, application) -> None:
        store = RememberingStore()
        made = self.window(store, RecordingPlayer())
        made.show()
        made.toggle_visualiser()
        assert store.get_setting(SETTING_VISUALISER) == TRUE
        made.toggle_visualiser()
        assert store.get_setting(SETTING_VISUALISER) == FALSE
        made.close()

    def test_it_comes_back_as_it_was_left(self, application) -> None:
        """A display that forgets itself is one you turn on every session."""
        made = self.window(
            RememberingStore({SETTING_VISUALISER: TRUE}), RecordingPlayer()
        )
        made.show()
        assert made._visualiser.isVisible()
        assert made._transport.visualising
        made.close()

    def test_the_menu_entry_agrees_with_the_strip(self, application) -> None:
        """Two ways of reading one state that could otherwise disagree."""
        made = self.window(RememberingStore(), RecordingPlayer())
        made.show()
        assert not made._visualiser_action.isChecked()
        made.toggle_visualiser()
        assert made._visualiser_action.isChecked()
        made.close()

    def test_it_runs_only_while_something_is_playing(self, application) -> None:
        """On show with nothing playing, there is nothing for it to draw."""
        player = RecordingPlayer()
        made = self.window(RememberingStore(), player)
        made.show()
        made.toggle_visualiser()
        assert not made._visualiser.running, "nothing is playing yet"
        player.state = PlaybackState.PLAYING
        made.follow_spectrum()
        assert made._visualiser.running
        player.state = PlaybackState.STOPPED
        made.follow_spectrum()
        assert not made._visualiser.running
        made.close()

    def test_a_hidden_strip_never_runs_however_the_music_goes(
        self, application
    ) -> None:
        player = RecordingPlayer()
        made = self.window(RememberingStore(), player)
        made.show()
        player.state = PlaybackState.PLAYING
        made.follow_spectrum()
        assert not made._visualiser.running
        made.close()
