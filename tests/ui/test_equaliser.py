"""The equalizer dialog, plus the window remembering what it was set to.

The dialog holds no state of its own: every move hands a whole curve outward,
which is what lets the sound change as a slider is dragged rather than when the
dialog is closed. So what is asserted is what it reported, plus that showing it
a curve does NOT report one back, which would make opening the dialog look like
a change to whatever it opened on.
"""

from __future__ import annotations

from playback_support import player, window
from PySide6.QtWidgets import QApplication

from stellody.domain.equalising import BAND_COUNT, FLAT_DB, Equalisation
from stellody.ui.equaliser import EqualiserDialog, band_label, gain_label
from stellody.ui.main_window import MainWindow
from stellody.ui.settings_keys import SETTING_EQ_ENABLED, SETTING_EQ_GAINS, TRUE

LIFT_DB = 5.0
__all__ = ["player", "window"]


def _dialog(parent, curve: Equalisation):
    """The dialog over a curve, recording what it hands back."""
    reported: list[Equalisation] = []
    made = EqualiserDialog(parent, curve, reported.append)
    return made, reported


class TestHowItReads:
    def test_a_frequency_below_a_thousand_is_said_in_hertz(self) -> None:
        """Which is how every equalizer a listener has met before labels it."""
        assert band_label(500) == "500"

    def test_a_frequency_above_a_thousand_is_said_in_kilohertz(self) -> None:
        """16000 on a slider is harder to read at a glance than 16k."""
        assert band_label(16000) == "16k"

    def test_a_gain_is_signed_so_a_cut_and_a_lift_are_told_apart(self) -> None:
        """Reading 3 where 3 was cut is the one mistake worth designing out."""
        assert gain_label(3) == "+3"
        assert gain_label(-3) == "-3"
        assert gain_label(0) == "+0"


class TestTheDialog:
    def test_it_opens_on_the_curve_it_was_given(self, window: MainWindow) -> None:
        """What it shows must be what is actually being applied."""
        curve = Equalisation(enabled=True).with_band(2, LIFT_DB)
        made, _ = _dialog(window, curve)
        assert made.switch.isChecked() is True
        assert made.bands[2].slider.value() == int(LIFT_DB)
        assert made.bands[2].reading.text() == gain_label(int(LIFT_DB))

    def test_opening_it_reports_nothing(self, window: MainWindow) -> None:
        """Otherwise opening the dialog would read as changing something."""
        _, reported = _dialog(window, Equalisation(enabled=True))
        assert reported == []

    def test_moving_a_band_reports_the_whole_curve(self, window: MainWindow) -> None:
        """The whole curve, because that is what the engine is designed from."""
        made, reported = _dialog(window, Equalisation(enabled=True))
        made.bands[4].slider.setValue(int(LIFT_DB))
        assert reported[-1].gains_db[4] == LIFT_DB
        assert reported[-1].enabled is True

    def test_the_reading_follows_the_handle(self, window: MainWindow) -> None:
        """A slider with no number on it is a slider nobody can set twice."""
        made, _ = _dialog(window, Equalisation(enabled=True))
        made.bands[0].slider.setValue(-4)
        assert made.bands[0].reading.text() == "-4"

    def test_switching_it_off_leaves_every_band_where_it_was(
        self, window: MainWindow
    ) -> None:
        """Comparing on against off must not cost somebody their settings."""
        curve = Equalisation(enabled=True).with_band(1, LIFT_DB)
        made, reported = _dialog(window, curve)
        made.switch.setChecked(False)
        assert reported[-1].enabled is False
        assert reported[-1].gains_db == curve.gains_db

    def test_flattening_levels_the_bands_and_leaves_the_switch(
        self, window: MainWindow
    ) -> None:
        """Two separate answers, so the one button moves only one of them."""
        curve = Equalisation(enabled=True).with_band(7, LIFT_DB)
        made, reported = _dialog(window, curve)
        made.flatten.click()
        assert reported[-1].gains_db == (FLAT_DB,) * BAND_COUNT
        assert reported[-1].enabled is True
        assert made.bands[7].slider.value() == 0


class TestRememberingIt:
    def test_a_curve_is_applied_and_written_down_together(
        self, window: MainWindow
    ) -> None:
        """A switch that forgets itself is the same as not having one."""
        curve = Equalisation(enabled=True).with_band(5, LIFT_DB)
        window.set_equalisation(curve)

        assert window._transport.equalisation == curve
        assert window._settings.get_setting(SETTING_EQ_ENABLED) == TRUE
        assert str(LIFT_DB) in window._settings.get_setting(SETTING_EQ_GAINS)

    def test_the_menu_opens_it_over_what_is_being_applied(
        self, window: MainWindow, application: QApplication
    ) -> None:
        """It is handed the transport's curve rather than reading one itself."""
        curve = Equalisation(enabled=True).with_band(6, -LIFT_DB)
        window.set_equalisation(curve)
        made = EqualiserDialog(
            window, window._transport.equalisation, lambda _curve: None
        )
        assert made.bands[6].slider.value() == int(-LIFT_DB)
