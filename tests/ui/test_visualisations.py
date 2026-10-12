"""The visualiser's ten named styles and the list the button lifts to choose one.

What is asserted is that every style draws something in silence and in sound,
that no two styles draw the same picture, that the button sits after the view
controls and lifts a list naming every style with the current one ticked, then
that a choice outlasts the window. Rendering the widget runs its own
paintEvent, so what is counted is what would be drawn rather than what is on
a screen.
"""

from __future__ import annotations

import pytest
from PySide6.QtGui import QColor, QImage
from PySide6.QtWidgets import QApplication
from recording_player import RecordingPlayer
from tray_support import RememberingStore, build

from stellody.domain.spectrum import BAR_COUNT, FULL, SILENT_BANDS
from stellody.ui.lift_menu import pop_up_above
from stellody.ui.palette import palette_for
from stellody.ui.settings_keys import SETTING_VISUALISATION
from stellody.ui.spectrum_styles import PAINTERS
from stellody.ui.theme import Mode, stylesheet
from stellody.ui.visualisations import (
    DEFAULT_VISUALISATION,
    NAMES,
    VISUALISATION_MENU,
    VISUALISATION_TOOLTIP,
    VISUALISATIONS,
    Visualisation,
    stored_visualisation,
)
from stellody.ui.visualiser import STRIP_MARGIN_PX, Visualiser

# Wide enough that every band gets its own columns of pixels to be counted in.
STRIP_WIDTH_PX = 600
STRIP_HEIGHT_PX = 68
# A spectrum with a shape, so a style that ignored the heights would show it.
SHAPED = tuple((band % 5 + 1) / 5 for band in range(BAR_COUNT))
LOUD = (FULL,) * BAR_COUNT
# The number of styles Oliver asked for: the four, then six more.
STYLE_COUNT = 10


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
    def test_there_are_ten_each_named_and_painted(self) -> None:
        assert len(VISUALISATIONS) == STYLE_COUNT
        assert set(NAMES) == set(VISUALISATIONS)
        assert set(PAINTERS) == set(VISUALISATIONS)
        assert len(set(NAMES.values())) == STYLE_COUNT, "no two share a name"

    def test_a_stored_name_comes_back_as_its_style(self) -> None:
        for style in VISUALISATIONS:
            assert stored_visualisation(style.value) is style

    def test_a_name_nobody_knows_falls_back_to_the_default(self) -> None:
        for stored in ("", "lasers", "3"):
            assert stored_visualisation(stored) is DEFAULT_VISUALISATION

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

    def test_every_style_but_the_bars_wears_more_than_one_colour(
        self, application: QApplication
    ) -> None:
        """Each carries colours of its own rather than the accent alone."""
        for mode in Mode:
            plain = len(_colours(_drawn(application, mode, Visualisation.BARS, LOUD)))
            for style in VISUALISATIONS:
                if style is Visualisation.BARS:
                    continue
                coloured = len(_colours(_drawn(application, mode, style, SHAPED)))
                assert coloured > plain, f"{style} in {mode}"


class TestTheRoom:
    """No style paints outside the room inside the strip's margin.

    Reported by Oliver on 2026-10-12: the rainbow's peak dots hung below the
    floor on quiet bands, measured at 320 pixels under it; the sunburst's hub
    did the same, at 32.
    """

    @pytest.mark.parametrize("style", VISUALISATIONS)
    def test_nothing_is_drawn_in_the_margin(
        self, application: QApplication, style: Visualisation
    ) -> None:
        ground = QColor(palette_for(Mode.DARK).surface).rgb()
        quiet = tuple(0.0 for _ in range(BAR_COUNT))
        low_peaks = tuple(0.05 for _ in range(BAR_COUNT))
        for shown, peaks in ((quiet, low_peaks), (LOUD, LOUD)):
            made = Visualiser(height_px=STRIP_HEIGHT_PX)
            made.show_appearance(Mode.DARK)
            made.show_style(style)
            made.resize(STRIP_WIDTH_PX, made.height())
            made._shown, made._peaks = shown, peaks
            image = made.grab().toImage()
            made.close()
            edge = STRIP_MARGIN_PX
            outside = [
                (x, y)
                for y in range(image.height())
                for x in range(image.width())
                if (
                    y < edge
                    or y >= image.height() - edge
                    or x < edge
                    or x >= image.width() - edge
                )
                and image.pixel(x, y) != ground
            ]
            assert outside == [], f"{style}: {len(outside)} pixels in the margin"


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


def _lines(window) -> list[tuple[str, bool]]:
    """What the list says, line by line, with whether each is ticked."""
    menu = window._bottom_tray.visualisation_menu
    return [(action.text(), action.isChecked()) for action in menu.actions()]


def _view_lines(window) -> list[tuple[str, bool]]:
    """What the View menu's copy of the list says, line by line."""
    return [(a.text(), a.isChecked()) for a in window._style_menu.actions()]


class TestTheList:
    def test_the_button_follows_the_view_controls_behind_a_rule(
        self, application
    ) -> None:
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
        assert button.toolTip() == VISUALISATION_TOOLTIP
        made.close()

    def test_it_names_every_style_with_the_one_in_force_ticked(
        self, application
    ) -> None:
        made = build(RememberingStore(), RecordingPlayer())
        assert _lines(made) == [
            (NAMES[style], style is DEFAULT_VISUALISATION) for style in VISUALISATIONS
        ]
        made.close()

    def test_the_button_lifts_it_and_a_second_press_puts_it_down(
        self, application
    ) -> None:
        made = build(RememberingStore(), RecordingPlayer())
        made.show()
        tray = made._bottom_tray
        menu = tray.visualisation_menu
        pop_up_above(menu, tray.visualisation_button)
        assert menu.isVisible()
        pop_up_above(menu, tray.visualisation_button)
        assert not menu.isVisible()
        made.close()

    def test_choosing_a_line_draws_it_ticks_it_and_writes_it_down(
        self, application
    ) -> None:
        store = RememberingStore()
        made = build(store, RecordingPlayer())
        menu = made._bottom_tray.visualisation_menu
        for style in reversed(VISUALISATIONS):
            line = next(a for a in menu.actions() if a.text() == NAMES[style])
            line.trigger()
            assert made._visualiser.style is style
            assert [ticked for _text, ticked in _lines(made)].count(True) == 1
            assert dict(_lines(made))[NAMES[style]]
            assert store.get_setting(SETTING_VISUALISATION) == style.value
        made.close()

    def test_the_view_menu_offers_the_same_list(self, application) -> None:
        """Oliver's ruling, 2026-10-12: the style list is on the menu bar too."""
        made = build(RememberingStore(), RecordingPlayer())
        view = made.menuBar().actions()[2].menu()
        style_entry = next(a for a in view.actions() if a.text() == VISUALISATION_MENU)
        assert _view_lines(made) == _lines(made)
        assert style_entry.menu() is made._style_menu
        made.close()

    def test_choosing_from_either_list_ticks_both(self, application) -> None:
        made = build(RememberingStore(), RecordingPlayer())
        from_menu = next(
            a
            for a in made._style_menu.actions()
            if a.text() == NAMES[Visualisation.FLAME]
        )
        from_menu.trigger()
        assert made._visualiser.style is Visualisation.FLAME
        assert dict(_lines(made))[NAMES[Visualisation.FLAME]]
        assert _view_lines(made) == _lines(made)
        strip = made._bottom_tray.visualisation_menu
        next(
            a for a in strip.actions() if a.text() == NAMES[Visualisation.SCOPE]
        ).trigger()
        assert dict(_view_lines(made))[NAMES[Visualisation.SCOPE]]
        assert _view_lines(made) == _lines(made)
        made.close()

    def test_a_reopened_window_draws_in_the_style_it_was_left_in(
        self, application
    ) -> None:
        for style in VISUALISATIONS:
            store = RememberingStore({SETTING_VISUALISATION: style.value})
            reopened = build(store, RecordingPlayer())
            assert reopened._visualiser.style is style
            assert dict(_lines(reopened))[NAMES[style]]
            reopened.close()
