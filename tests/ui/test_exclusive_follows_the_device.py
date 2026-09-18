"""Exclusive output is offered only for a song the device in use can take.

Ruled by Oliver on 2026-09-18, after moving from his speakers to his Focal
Bathys and seeing nothing change. The Bathys takes exclusive output at 48 kHz
alone, so a 44.1 kHz song, which is most of a CD collection, cannot have it
there. Offering the switch for such a song is the same misleading offer a lossy
file is, so it stands down the same way: the house red rounded rectangle, the
reason in its tooltip, the saved choice left exactly as it was. The menu entry
follows the switch.

A move of the output is a new device, so the question is asked again then,
rather than only once at startup.
"""

from __future__ import annotations

from playback_support import BareStore, player, window
from PySide6.QtWidgets import QApplication
from recording_player import RecordingPlayer
from test_no_exclusive_for_a_lossy_song import played, switch

from stellody.application.loading import LoadLibrary
from stellody.application.scan import ScanLibrary
from stellody.application.transport import Transport
from stellody.domain.album import Album
from stellody.domain.identity import AlbumIdentity
from stellody.domain.playback import OutputMode
from stellody.domain.track import CD_SAMPLE_RATE, Track, TrackSource
from stellody.infrastructure.wasapi import NO_EXCLUSIVE_FORMAT
from stellody.ui.main_window import MainWindow
from stellody.ui.settings_keys import SETTING_OUTPUT_MODE
from stellody.ui.sound_controls import SHARED_TOOLTIP
from stellody.ui.switches import NO_RATES_AT_ALL, NOT_FOR_THIS_LIBRARY

__all__ = ["player", "window"]

CD_ROW = 0
STUDIO_ROW = 1
# What a CD holds and what a download commonly holds; the Bathys takes the
# second alone, measured on 2026-09-18.
STUDIO_RATE = 48000
BATHYS = (STUDIO_RATE,)
SPEAKERS = (CD_SAMPLE_RATE, STUDIO_RATE)
DEPTH = 16


def song(number: int, rate: int) -> Track:
    """One lossless track at that rate."""
    return Track(
        source=TrackSource(path=f"{number}.flac"),
        disc_number=1,
        track_number=number,
        title=f"Track {number}",
        artists=("Holst",),
        duration_ms=1000,
        sample_rate=rate,
        bit_depth=DEPTH,
    )


def rates_apart() -> Album:
    """A 44.1 kHz song then a 48 kHz one."""
    return Album(
        identity=AlbumIdentity(album_artist="Holst", title="The Planets"),
        tracks=(song(1, CD_SAMPLE_RATE), song(2, STUDIO_RATE)),
    )


def on(made: MainWindow, player: RecordingPlayer, rates) -> MainWindow:
    """The window over that album, on a device taking those rates."""
    made._model.set_albums((rates_apart(),))
    player.rates = rates
    return made


def sound_entry(made: MainWindow):
    """The Sound menu's entry, read as it is when the menu opens."""
    made._show_mirrored_state()
    return made._exclusive_action


def test_a_song_at_a_rate_the_device_refuses_stands_it_down(
    window: MainWindow, player: RecordingPlayer
) -> None:
    made = on(window, player, BATHYS)
    played(made, CD_ROW)
    assert not switch(made).isEnabled()
    said = switch(made).toolTip()
    assert "48 kHz" in said and "44.1 kHz" in said


def test_a_song_at_a_rate_it_takes_is_offered_it(
    window: MainWindow, player: RecordingPlayer
) -> None:
    """Guard the guard: standing it down for every song would pass above."""
    made = on(window, player, BATHYS)
    played(made, STUDIO_ROW)
    assert switch(made).isEnabled()


def test_the_menu_follows_the_switch(
    window: MainWindow, player: RecordingPlayer
) -> None:
    """What Oliver saw: the menu offering what the strip could not deliver."""
    made = on(window, player, BATHYS)
    played(made, CD_ROW)
    assert not sound_entry(made).isEnabled()
    played(made, STUDIO_ROW)
    assert sound_entry(made).isEnabled()


def test_the_choice_is_kept_through_a_song_the_device_refuses(
    window: MainWindow, player: RecordingPlayer
) -> None:
    """The lossy ruling, applied to a rate: the next song it can take has it."""
    made = on(window, player, BATHYS)
    made.toggle_exclusive()
    # Refused as the real device refuses a rate it does not list.
    player.grants = False
    player.refusal = NO_EXCLUSIVE_FORMAT
    played(made, CD_ROW)
    player.grants = True
    assert made._transport.output_mode is OutputMode.EXCLUSIVE
    assert made._settings.get_setting(SETTING_OUTPUT_MODE) == (
        OutputMode.EXCLUSIVE.value
    )
    assert "refused" not in made.statusBar().currentMessage()
    played(made, STUDIO_ROW)
    assert switch(made).isEnabled()
    assert switch(made).toolTip() == SHARED_TOOLTIP


def test_the_highlighted_song_decides_while_nothing_is_loaded(
    window: MainWindow, player: RecordingPlayer
) -> None:
    """His second screenshot: a song highlighted, nothing playing yet."""
    made = on(window, player, BATHYS)
    album_row = made._model.index(0, 0)
    made._tree.setCurrentIndex(made._model.index(CD_ROW, 0, album_row))
    made._show_transport()
    assert not switch(made).isEnabled()


def test_a_move_of_the_output_asks_again(
    window: MainWindow, player: RecordingPlayer
) -> None:
    """Speakers to the Bathys, then back: the switch follows each move."""
    made = on(window, player, SPEAKERS)
    played(made, CD_ROW)
    assert switch(made).isEnabled()
    player.rates = BATHYS
    made.output_moved()
    assert not switch(made).isEnabled()
    player.rates = SPEAKERS
    made.output_moved()
    assert switch(made).isEnabled()


def held(made: MainWindow, *albums: Album) -> MainWindow:
    """The window told the library holds these, as a load or a scan tells it."""
    made.show_library(albums, ())
    return made


def cd_album() -> Album:
    """Lossless songs at the CD rate alone."""
    return Album(
        identity=AlbumIdentity(album_artist="Holst", title="The Planets"),
        tracks=(song(1, CD_SAMPLE_RATE), song(2, CD_SAMPLE_RATE)),
    )


class TestWithNothingSelected:
    """Ruled by Oliver on 2026-09-18: nothing selected is not nothing to judge.

    With no song in hand the device is judged against the library: the switch
    is offered only where the device takes the rate of at least one lossless
    song the library holds. A device fitting none of the music is the wrong
    device, which he found as misleading as a wrong song; the reverse holds
    too, so the right device brings the switch back.
    """

    def test_a_device_fitting_none_of_the_library_stands_it_down(
        self, window: MainWindow, player: RecordingPlayer
    ) -> None:
        made = held(window, cd_album())
        player.rates = BATHYS
        made._show_transport()
        assert not switch(made).isEnabled()
        assert switch(made).toolTip() == NOT_FOR_THIS_LIBRARY.format(rates="48 kHz")
        assert not sound_entry(made).isEnabled()

    def test_a_device_fitting_some_of_it_offers_it(
        self, window: MainWindow, player: RecordingPlayer
    ) -> None:
        """One lossless song it can take is enough to offer the switch."""
        made = held(window, rates_apart())
        player.rates = BATHYS
        made._show_transport()
        assert switch(made).isEnabled()

    def test_a_lossy_song_at_its_rate_is_no_reason_to_offer_it(
        self, window: MainWindow, player: RecordingPlayer
    ) -> None:
        lossy_studio = Album(
            identity=AlbumIdentity(album_artist="Holst", title="Mars"),
            tracks=(
                Track(
                    source=TrackSource(path="1.mp3"),
                    disc_number=1,
                    track_number=1,
                    title="Mars",
                    artists=("Holst",),
                    duration_ms=1000,
                    sample_rate=STUDIO_RATE,
                    bit_depth=0,
                ),
            ),
        )
        made = held(window, cd_album(), lossy_studio)
        player.rates = BATHYS
        made._show_transport()
        assert not switch(made).isEnabled()

    def test_the_right_device_brings_it_back_and_the_wrong_one_takes_it(
        self, window: MainWindow, player: RecordingPlayer
    ) -> None:
        """Both directions, across moves of the output."""
        made = held(window, cd_album())
        player.rates = BATHYS
        made.output_moved()
        assert not switch(made).isEnabled()
        player.rates = SPEAKERS
        made.output_moved()
        assert switch(made).isEnabled()
        player.rates = BATHYS
        made.output_moved()
        assert not switch(made).isEnabled()

    def test_a_library_not_yet_known_stands_nothing_down(
        self, window: MainWindow, player: RecordingPlayer
    ) -> None:
        """Before the first load there is no answer; nothing lossless gives none."""
        made = held(window)
        player.rates = BATHYS
        made._show_transport()
        assert switch(made).isEnabled()


def test_a_device_taking_nothing_is_not_stood_down_for_good(
    application: QApplication,
) -> None:
    """A move can bring a device that does take something."""
    store = BareStore()
    player = RecordingPlayer()
    player.rates = ()

    def session():
        return ScanLibrary(None, None, None, store), store

    made = MainWindow(
        scan_session=session,
        loader=LoadLibrary(store),
        transport=Transport(player),
        settings=store,
    )
    made._model.set_albums((rates_apart(),))
    made.restore_switches()
    assert not switch(made).isEnabled()
    assert switch(made).toolTip() == NO_RATES_AT_ALL
    player.rates = SPEAKERS
    made.output_moved()
    assert switch(made).isEnabled()
