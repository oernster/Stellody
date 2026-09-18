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
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QApplication
from recording_player import RecordingPlayer
from tray_support import wears_the_dead_ring

from stellody.application.loading import LoadLibrary
from stellody.application.scan import ScanLibrary
from stellody.application.transport import Transport
from stellody.domain.playback import OutputMode
from stellody.ui.main_window import MainWindow
from stellody.ui.settings_keys import SETTING_OUTPUT_MODE
from stellody.ui.sound_controls import EXCLUSIVE_TOOLTIP, SHARED_TOOLTIP
from stellody.ui.theme import palette_for

__all__ = ["player", "window"]

REFUSAL = "Exclusive output is not offered on Linux"


def switch(made: MainWindow):
    """The control itself."""
    return made._bottom_tray.sound.exclusive_button


def built_with(
    application: QApplication,
    store: BareStore,
    refusal: str,
    rates: tuple[int, ...] | None = (44100,),
) -> MainWindow:
    """A window over that store, told what the platform and device allow."""

    def session():
        return ScanLibrary(None, None, None, store), store

    player = RecordingPlayer()
    player.rates = rates
    made = MainWindow(
        scan_session=session,
        loader=LoadLibrary(store),
        transport=Transport(player),
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


class TestWhenTheDeviceRefuses:
    """Oliver ruled on this on 2026-09-18, after seeing it on his own machine.

    The switch had stayed struck through over a mixer stream, because it was
    built to show the CHOICE. A picture saying exclusive while the mixer plays
    is the one thing every other switch here is careful not to do, so a refusal
    now takes it back to shared and says so in words.

    Measured the same day on his Focal Bathys: exclusive mode is offered at
    48 kHz int16 and at no other rate, so a 44.1 kHz album is refused before
    the device is even opened. This is not a rare path.
    """

    def refused(self, made: MainWindow, player: RecordingPlayer) -> None:
        """Ask for exclusive output on a device that will not give it."""
        from playback_support import track_index

        player.grants = False
        player.refusal = "the device is in use"
        made.toggle_exclusive()
        made.activate(track_index(made, 0))
        made._poll_transport()

    def test_the_switch_goes_back_to_shared(
        self, window: MainWindow, player: RecordingPlayer
    ) -> None:
        self.refused(window, player)
        assert window._transport.output_mode is OutputMode.SHARED

    def test_the_picture_goes_back_with_it(
        self, window: MainWindow, player: RecordingPlayer
    ) -> None:
        """The whole of what he reported: the icon had stayed changed."""
        plain = switch(window).icon().pixmap(32).toImage()
        self.refused(window, player)
        assert switch(window).icon().pixmap(32).toImage() == plain
        assert switch(window).toolTip() == EXCLUSIVE_TOOLTIP

    def test_a_refusal_at_a_rate_it_lists_gives_the_devices_own_reason(
        self, window: MainWindow, player: RecordingPlayer
    ) -> None:
        """Another application holding it, say: the rates are no answer then.

        A rate the device does not list never gets this far since
        2026-09-18: such a song is not offered the switch at all, with the
        rates it does take in the tooltip instead. See
        `test_exclusive_follows_the_device.py`.
        """
        player.rates = (44100, 48000)
        self.refused(window, player)
        said = window.statusBar().currentMessage()
        assert "Exclusive output was refused" in said
        assert "the device is in use" in said

    def test_a_device_that_cannot_be_asked_falls_back_to_its_own_reason(
        self, window: MainWindow, player: RecordingPlayer
    ) -> None:
        """A platform that may not be probed says what the device said instead."""
        player.rates = None
        self.refused(window, player)
        said = window.statusBar().currentMessage()
        assert "Exclusive output was refused" in said
        assert "the device is in use" in said

    def test_the_readout_carries_no_refusal(
        self, window: MainWindow, player: RecordingPlayer
    ) -> None:
        """It describes the open stream, which really is the mixer now."""
        self.refused(window, player)
        assert "refused" not in window._position_bar.stream.text()

    def test_a_device_that_said_nothing_is_not_given_words(
        self, window: MainWindow, player: RecordingPlayer
    ) -> None:
        """Inventing a reason would be worse than admitting there is none."""
        from playback_support import track_index

        player.grants = False
        player.refusal = ""
        player.rates = None
        window.toggle_exclusive()
        window.activate(track_index(window, 0))
        window._poll_transport()
        assert "did not say why" in window.statusBar().currentMessage()

    def test_it_is_said_once_rather_than_four_times_a_second(
        self, window: MainWindow, player: RecordingPlayer
    ) -> None:
        """Standing down is what stops it; without that the poll would repeat."""
        self.refused(window, player)
        window.statusBar().clearMessage()
        for _ in range(4):
            window._poll_transport()
        assert window.statusBar().currentMessage() == ""

    def test_the_music_is_not_reopened_on_the_way_down(
        self, window: MainWindow, player: RecordingPlayer
    ) -> None:
        """A refused stream is already the mixer, so a reopen is a gap for nothing."""
        self.refused(window, player)
        player.calls.clear()
        window._poll_transport()
        assert "load" not in player.calls

    def test_a_granted_request_is_left_alone(
        self, window: MainWindow, player: RecordingPlayer
    ) -> None:
        """Guard the guard: standing down on every poll would pass the rest."""
        from playback_support import track_index

        window.toggle_exclusive()
        window.activate(track_index(window, 0))
        window._poll_transport()
        assert window._transport.output_mode is OutputMode.EXCLUSIVE
        assert window.statusBar().currentMessage() == ""


class TestADeviceThatTakesNoneAtAll:
    """The device half of the rule the platform half follows, until a move.

    Oliver on 2026-09-18: a control offering a mode the machine cannot deliver
    is misleading, whether what cannot deliver it is the operating system or
    the sound device in front of it. Neither leaves a press that would achieve
    anything, so both stand the control down.
    """

    def test_the_control_is_stood_down_with_the_reason_on_it(
        self, application: QApplication
    ) -> None:
        store = BareStore()
        made = built_with(application, store, refusal="", rates=())
        assert not switch(made).isEnabled()
        assert "no exclusive output at any sample rate" in switch(made).toolTip()

    def test_it_wears_the_red_rounded_rectangle_every_dead_control_wears(
        self, application: QApplication
    ) -> None:
        """Asked for by name on 2026-09-18; it is the house disabled rule."""
        made = built_with(application, BareStore(), refusal="", rates=())
        danger = QColor(palette_for(made.theme_mode).danger).name()
        assert wears_the_dead_ring(switch(made), danger)

    def test_a_device_that_takes_something_keeps_the_control(
        self, application: QApplication
    ) -> None:
        """Guard the guard: standing it down always would pass the two above."""
        made = built_with(application, BareStore(), refusal="", rates=(48000,))
        assert switch(made).isEnabled()

    def test_a_platform_that_cannot_be_asked_keeps_the_control(
        self, application: QApplication
    ) -> None:
        """An unanswered question is not a no."""
        made = built_with(application, BareStore(), refusal="", rates=None)
        assert switch(made).isEnabled()

    def test_the_choice_is_kept_where_the_device_takes_none(
        self, application: QApplication
    ) -> None:
        """Since 2026-09-18 a move of the output can bring a device that does.

        The choice stands, as it does through a lossy song, so the first
        device that takes the song's rate gets exclusive output with no press.
        Asked of such a device meanwhile, a request is answered by the mixer.
        """
        store = BareStore()
        store.set_setting(SETTING_OUTPUT_MODE, OutputMode.EXCLUSIVE.value)
        made = built_with(application, store, refusal="", rates=())
        assert made._transport.output_mode is OutputMode.EXCLUSIVE
        assert store.get_setting(SETTING_OUTPUT_MODE) == OutputMode.EXCLUSIVE.value
