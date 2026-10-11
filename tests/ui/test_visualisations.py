"""The visualiser's four styles and the button that steps between them.

What is asserted is that every style draws something in silence and in sound,
that no two styles draw the same picture, that the button sits after the view
controls and says where a press goes, then that the choice outlasts the window.
Rendering the widget runs its own paintEvent, so what is counted is what would
be drawn rather than what is on a screen.
"""

from __future__ import annotations

import pytest
from PySide6.QtGui import QImage
from PySide6.QtWidgets import QApplication
from recording_player import RecordingPlayer
from tray_support import RememberingStore, build

from stellody.domain.spectrum import BAR_COUNT, FULL, SILENT_BANDS
from stellody.ui.settings_keys import SETTING_VISUALISATION
from stellody.ui.theme import Mode, stylesheet
from stellody.ui.visualisations import (
    DEFAULT_VISUALISATION,
    VISUALISATIONS,
    Visualisation,
    next_visualisation,
    stored_visualisation,
    visualisation_tooltip,
)
from stellody.ui.visualiser import Visualiser

# Wide enough that every band gets its own columns of pixels to be counted in.
STRIP_WIDTH_PX = 600
STRIP_HEIGHT_PX = 34
# A spectrum with a shape, so a style that ignored the heights would show it.
SHAPED = tuple((band % 5 + 1) / 5 for band in range(BAR_COUNT))
LOUD = (FULL,) * BAR_COUNT


def _drawn(
    application: QApplication, mode: Mode, style: Visualisation, heights
) -> QImage:
    """What one style paints over these heights, in this appearance."""
    application.setStyleSheet(stylesheet(mode))
    made = Visualiser(height_px=STRIP_HEIGHT_PX)
    made.show_appearance(mode)
    made.show_style(style)
    made.resize(STRIP_WIDTH_PX, made.height())
    made.read_levels_from(lambda: heights)
    made._tick()
    made.show()
    application.processEvents()
    image = made.grab().toImage()
    made.stop()
    made.close()
    return image


def _colours(image: QImage) -> set[int]:
    return {
        image.pixel(x, y)
        for y in range(0, image.height(), 2)
        for x in range(0, image.width(), 4)
    }


class TestTheStyles:
    def test_a_press_steps_through_every_style_and_comes_round(self) -> None:
        seen = [DEFAULT_VISUALISATION]
        for _ in VISUALISATIONS:
            seen.append(next_visualisation(seen[-1]))
        assert set(seen) == set(VISUALISATIONS)
        assert seen[-1] is DEFAULT_VISUALISATION

    def test_a_stored_name_comes_back_as_its_style(self) -> None:
        for style in VISUALISATIONS:
            assert stored_visualisation(style.value) is style

    def test_a_name_nobody_knows_falls_back_to_the_bars(self) -> None:
        for stored in ("", "lasers", "3"):
            assert stored_visualisation(stored) is DEFAULT_VISUALISATION

    def test_the_tooltip_names_where_a_press_goes(self) -> None:
        assert visualisation_tooltip(Visualisation.WAVE).endswith("the wave")

    @pytest.mark.parametrize("style", VISUALISATIONS)
    def test_silence_still_reads_as_a_strip_in_every_style(
        self, application: QApplication, style: Visualisation
    ) -> None:
        for mode in Mode:
            drawn = _drawn(application, mode, style, SILENT_BANDS)
            assert len(_colours(drawn)) > 1, f"{style} in {mode}: one flat colour"

    @pytest.mark.parametrize("mode", list(Mode))
    def test_no_two_styles_draw_the_same_picture(
        self, application: QApplication, mode: Mode
    ) -> None:
        drawn = {
            style: _drawn(application, mode, style, SHAPED) for style in VISUALISATIONS
        }
        for style in VISUALISATIONS:
            for other in VISUALISATIONS:
                if style is not other:
                    assert drawn[style] != drawn[other], f"{style} draws as {other}"

    def test_the_new_styles_wear_more_than_one_colour(
        self, application: QApplication
    ) -> None:
        """Each of the three carries a ramp of its own rather than the accent."""
        for mode in Mode:
            plain = len(_colours(_drawn(application, mode, Visualisation.BARS, LOUD)))
            for style in VISUALISATIONS:
                if style is Visualisation.BARS:
                    continue
                coloured = len(_colours(_drawn(application, mode, style, LOUD)))
                assert coloured > plain, f"{style} in {mode}"


class TestThePeaks:
    def test_a_peak_hangs_after_the_bar_falls(self, application) -> None:
        made = Visualiser()
        made.read_levels_from(lambda: LOUD)
        made._tick()
        made.read_levels_from(lambda: SILENT_BANDS)
        made._tick()
        assert all(peak > bar for peak, bar in zip(made.peaks, made.shown))
        made.close()

    def test_stopping_clears_the_peaks_too(self, application) -> None:
        made = Visualiser()
        made.read_levels_from(lambda: LOUD)
        made.start()
        made._tick()
        made.stop()
        assert made.peaks == SILENT_BANDS
        made.close()


class TestTheButton:
    def test_it_follows_the_view_controls_behind_a_rule(self, application) -> None:
        made = build(RememberingStore(), RecordingPlayer())
        made.show()
        tray = made._bottom_tray

        def across(widget) -> int:
            return widget.mapTo(tray, widget.rect().center()).x()

        last_view = tray.showing.stops()[-1]
        rule, button = tray.visualisation_separator, tray.visualisation_button
        assert across(last_view) < across(rule) < across(button)
        assert across(button) < across(tray.visualiser), "still in the left group"
        stops = tray.ring_stops()
        assert stops.index(button) == stops.index(last_view) + 1
        assert not button.icon().isNull(), "it wears the artwork"
        made.close()

    def test_a_press_steps_the_style_and_writes_it_down(self, application) -> None:
        store = RememberingStore()
        made = build(store, RecordingPlayer())
        button = made._bottom_tray.visualisation_button
        style = made._visualiser.style
        for _ in VISUALISATIONS:
            following = next_visualisation(style)
            assert button.toolTip() == visualisation_tooltip(following)
            button.click()
            style = made._visualiser.style
            assert style is following
            assert store.get_setting(SETTING_VISUALISATION) == style.value
        made.close()

    def test_a_reopened_window_draws_in_the_style_it_was_left_in(
        self, application
    ) -> None:
        for style in VISUALISATIONS:
            store = RememberingStore({SETTING_VISUALISATION: style.value})
            reopened = build(store, RecordingPlayer())
            assert reopened._visualiser.style is style
            reopened.close()
