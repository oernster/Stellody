"""The switch between shared and exclusive output, on the bottom strip.

Asked for by Oliver on 2026-09-17, with the artwork and the order both stated
by him: volume, mute, a rule, exclusive output, the equalizer. Where it sits is
asserted in `test_volume_level.py` with the rest of the strip; what a press
does and what the picture says are here.

**The picture says what a press would DO**, which is the rule every switch in
this application follows. Plain artwork while the device is shared, because
that press takes it; struck through while it is held, because that press gives
it back. Stated in his own words: "The states of the buttons image-wise should
always describe what the button is going TO, not what it is right now."
"""

from __future__ import annotations

import pytest
from playback_support import BareStore, album, player, window
from PySide6.QtWidgets import QApplication
from recording_player import RecordingPlayer

from stellody.application.loading import LoadLibrary
from stellody.application.scan import ScanLibrary
from stellody.application.transport import Transport
from stellody.domain.playback import OutputMode
from stellody.ui.main_window import MainWindow
from stellody.ui.settings_keys import SETTING_OUTPUT_MODE
from stellody.ui.sound_controls import EXCLUSIVE_TOOLTIP, SHARED_TOOLTIP

__all__ = ["player", "window"]

REFUSAL = "Exclusive output is not offered on Linux"


def switch(made: MainWindow):
    """The control itself."""
    return made._bottom_tray.sound.exclusive_button


def built_with(application: QApplication, store: BareStore, refusal: str) -> MainWindow:
    """A window over that store, told whether this platform offers the mode."""

    def session():
        return ScanLibrary(None, None, None, store), store

    made = MainWindow(
        scan_session=session,
        loader=LoadLibrary(store),
        transport=Transport(RecordingPlayer()),
        settings=store,
        exclusive_refusal=refusal,
    )
    made._model.set_albums((album(),))
    made.restore_switches()
    return made


class TestWhatAPressDoes:
    def test_it_asks_the_transport_for_exclusive_output(
        self, window: MainWindow
    ) -> None:
        window.toggle_exclusive()
        assert window._transport.output_mode is OutputMode.EXCLUSIVE

    def test_a_second_press_goes_back_to_sharing_the_device(
        self, window: MainWindow
    ) -> None:
        window.toggle_exclusive()
        window.toggle_exclusive()
        assert window._transport.output_mode is OutputMode.SHARED

    def test_the_tooltip_names_what_the_next_press_would_do(
        self, window: MainWindow
    ) -> None:
        assert switch(window).toolTip() == EXCLUSIVE_TOOLTIP
        window.toggle_exclusive()
        assert switch(window).toolTip() == SHARED_TOOLTIP

    def test_the_artwork_is_struck_through_only_while_it_is_held(
        self, window: MainWindow
    ) -> None:
        """His rule for every switch: the picture is the destination.

        The two icons are compared as images rather than by name, since a
        struck picture is built rather than loaded and has no name of its own.
        """
        shared = switch(window).icon().pixmap(32).toImage()
        window.toggle_exclusive()
        exclusive = switch(window).icon().pixmap(32).toImage()
        assert shared != exclusive
        window.toggle_exclusive()
        assert switch(window).icon().pixmap(32).toImage() == shared


class TestWhatIsRemembered:
    def test_the_choice_is_written_down(self, window: MainWindow) -> None:
        window.toggle_exclusive()
        assert window._settings.get_setting(SETTING_OUTPUT_MODE) == (
            OutputMode.EXCLUSIVE.value
        )

    def test_it_comes_back_as_it_was_left(
        self, application: QApplication, window: MainWindow
    ) -> None:
        """A switch that forgets itself is the same as not having one."""
        store = BareStore()
        store.set_setting(SETTING_OUTPUT_MODE, OutputMode.EXCLUSIVE.value)
        made = built_with(application, store, refusal="")
        assert made._transport.output_mode is OutputMode.EXCLUSIVE
        assert switch(made).toolTip() == SHARED_TOOLTIP

    @pytest.mark.parametrize("stored", ["", "loud", "EXCLUSIVE"])
    def test_anything_that_is_not_a_mode_reads_as_shared(
        self, application: QApplication, stored: str
    ) -> None:
        """A silent machine nobody can explain is the failure to avoid."""
        store = BareStore()
        store.set_setting(SETTING_OUTPUT_MODE, stored)
        made = built_with(application, store, refusal="")
        assert made._transport.output_mode is OutputMode.SHARED


class TestWherePlatformOffersNoRoute:
    def test_the_control_is_stood_down_with_the_reason_on_it(
        self, application: QApplication
    ) -> None:
        """A control that can do nothing is worse than no control."""
        made = built_with(application, BareStore(), refusal=REFUSAL)
        assert not switch(made).isEnabled()
        assert switch(made).toolTip() == REFUSAL

    def test_the_mode_opens_shared_whatever_the_setting_says(
        self, application: QApplication
    ) -> None:
        store = BareStore()
        store.set_setting(SETTING_OUTPUT_MODE, OutputMode.EXCLUSIVE.value)
        made = built_with(application, store, refusal=REFUSAL)
        assert made._transport.output_mode is OutputMode.SHARED

    def test_the_choice_written_down_is_left_exactly_as_it_was(
        self, application: QApplication
    ) -> None:
        """A machine that cannot honour a choice does not get to erase it."""
        store = BareStore()
        store.set_setting(SETTING_OUTPUT_MODE, OutputMode.EXCLUSIVE.value)
        built_with(application, store, refusal=REFUSAL)
        assert store.get_setting(SETTING_OUTPUT_MODE) == OutputMode.EXCLUSIVE.value

    def test_a_window_told_nothing_offers_the_control(
        self, application: QApplication
    ) -> None:
        """Guard the guard: a control disabled everywhere would pass above."""
        made = built_with(application, BareStore(), refusal="")
        assert switch(made).isEnabled()


class TestWhatTheStripShows:
    def test_the_poll_keeps_the_readout_current(self, window: MainWindow) -> None:
        """The report belongs to the open stream, so it follows the track."""
        from playback_support import track_index

        window.activate(track_index(window, 0))
        window._poll_transport()
        assert window._position_bar.stream.text().startswith("shared")

    def test_nothing_playing_says_nothing(self, window: MainWindow) -> None:
        window._poll_transport()
        assert window._position_bar.stream.text() == ""

    def test_a_refused_request_is_named_on_screen(
        self, window: MainWindow, player: RecordingPlayer
    ) -> None:
        """The case the readout exists for: the choice stands, the stream did not."""
        from playback_support import track_index

        player.grants = False
        player.refusal = "the device is in use"
        window.toggle_exclusive()
        window.activate(track_index(window, 0))
        window._poll_transport()
        said = window._position_bar.stream.text()
        assert "exclusive refused: the device is in use" in said
        assert window._transport.output_mode is OutputMode.EXCLUSIVE, "choice stands"
