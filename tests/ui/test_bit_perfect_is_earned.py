"""The stream line claims bit perfect only while nothing alters the samples.

Found by reading on 2026-10-02: the line judged the opened stream alone, so an
exclusive native stream read "bit perfect" with the volume turned down or an
equalizer curve applied, both of which change every sample on its way out.

A curve switched on but left flat is the case that must stay bit perfect: the
equalizer designs no sections for it and the engine hands the block back
untouched, so the claim is still true.
"""

from __future__ import annotations

from playback_support import player, track_index, window

from stellody.domain.equalising import Equalisation
from stellody.ui.main_window import MainWindow
from stellody.ui.stream_words import BIT_PERFECT

__all__ = ["player", "window"]

FULL_PERCENT = 100
TURNED_DOWN_PERCENT = 50
LIFT_DB = 3.0
FIRST_BAND = 0


def playing_exclusively(made: MainWindow) -> MainWindow:
    """The first track open on an exclusive stream at its own rate and depth."""
    made.toggle_exclusive()
    made.activate(track_index(made, 0))
    made._poll_transport()
    return made


def said(made: MainWindow) -> str:
    """What the line beside the clock reads."""
    return made._position_bar.stream.text()


class TestOnlyAnUntouchedStreamIsBitPerfect:
    def test_at_full_volume_with_no_curve_it_is(self, window: MainWindow) -> None:
        """Guard the guard: the cases below would pass on a line never saying it."""
        window.set_volume(FULL_PERCENT)
        assert said(playing_exclusively(window)).endswith(BIT_PERFECT)

    def test_a_volume_below_full_takes_the_claim_away(self, window: MainWindow) -> None:
        window.set_volume(TURNED_DOWN_PERCENT)
        assert BIT_PERFECT not in said(playing_exclusively(window))

    def test_muting_takes_it_away_too(self, window: MainWindow) -> None:
        """Silence is every sample changed, whatever level is remembered."""
        window.set_volume(FULL_PERCENT)
        window.toggle_mute()
        assert BIT_PERFECT not in said(playing_exclusively(window))

    def test_a_curve_that_shapes_the_sound_takes_it_away(
        self, window: MainWindow
    ) -> None:
        window.set_volume(FULL_PERCENT)
        window.set_equalisation(
            Equalisation(enabled=True).with_band(FIRST_BAND, LIFT_DB)
        )
        assert BIT_PERFECT not in said(playing_exclusively(window))

    def test_a_flat_curve_switched_on_leaves_it_standing(
        self, window: MainWindow
    ) -> None:
        """No section is designed for it, so not one sample is touched."""
        window.set_volume(FULL_PERCENT)
        window.set_equalisation(Equalisation(enabled=True))
        assert said(playing_exclusively(window)).endswith(BIT_PERFECT)


class TestTheLineFollowsTheSettings:
    def test_turning_the_volume_down_mid_track_withdraws_it(
        self, window: MainWindow
    ) -> None:
        window.set_volume(FULL_PERCENT)
        playing_exclusively(window)
        window.set_volume(TURNED_DOWN_PERCENT)
        assert BIT_PERFECT not in said(window)

    def test_turning_it_back_up_restores_it(self, window: MainWindow) -> None:
        window.set_volume(TURNED_DOWN_PERCENT)
        playing_exclusively(window)
        window.set_volume(FULL_PERCENT)
        assert said(window).endswith(BIT_PERFECT)

    def test_muting_mid_track_withdraws_it(self, window: MainWindow) -> None:
        window.set_volume(FULL_PERCENT)
        playing_exclusively(window)
        window.toggle_mute()
        assert BIT_PERFECT not in said(window)

    def test_switching_a_curve_on_mid_track_withdraws_it(
        self, window: MainWindow
    ) -> None:
        window.set_volume(FULL_PERCENT)
        playing_exclusively(window)
        window.set_equalisation(
            Equalisation(enabled=True).with_band(FIRST_BAND, LIFT_DB)
        )
        assert BIT_PERFECT not in said(window)
