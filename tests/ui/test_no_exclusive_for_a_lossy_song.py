"""Exclusive output is not offered while the song in hand is lossy.

Ruled by Oliver on 2026-09-18: a lossy file holds no bit depth to deliver
untouched, so offering exclusive output for one is a misleading hi-fi offer.
The switch stands down for it exactly as it does where the device or the
platform cannot deliver the mode, wearing the house red rounded rectangle with
the reason in its tooltip.

The choice is the listener's and outlives one song, also his ruling of the
same day: a lossy song leaves it exactly as it was, so the next lossless song
plays exclusively again with no press, while a listener who never chose it
gets the switch back showing shared. What it must no longer do is what it did
before: take the file's refusal for the device's, save shared over the choice
and blame the song's rate on the status line, which named as refused the very
rate it said the device takes.
"""

from __future__ import annotations

from playback_support import BareStore, player, window
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QApplication
from recording_player import RecordingPlayer
from tray_support import wears_the_dead_ring

from stellody.application.loading import LoadLibrary
from stellody.application.scan import ScanLibrary
from stellody.application.transport import Transport
from stellody.domain.album import Album
from stellody.domain.identity import AlbumIdentity
from stellody.domain.playback import OutputMode
from stellody.domain.track import CD_SAMPLE_RATE, Track, TrackSource
from stellody.infrastructure.portaudio import NO_STATED_DEPTH
from stellody.ui.main_window import MainWindow
from stellody.ui.settings_keys import SETTING_OUTPUT_MODE
from stellody.ui.sound_controls import (
    EXCLUSIVE_TOOLTIP,
    LOSSY_TOOLTIP,
    SHARED_TOOLTIP,
)
from stellody.ui.theme import palette_for

__all__ = ["player", "window"]

LOSSLESS_ROW = 0
LOSSY_ROW = 1
# What a lossless rip states and what a lossy one states: nought is unstated.
STATED_DEPTH = 16
NO_DEPTH = 0
PLATFORM_REFUSAL = "Exclusive output is not offered on Linux."


def song(number: int, suffix: str, depth: int) -> Track:
    """One track of the mixed album."""
    return Track(
        source=TrackSource(path=f"{number}.{suffix}"),
        disc_number=1,
        track_number=number,
        title=f"Track {number}",
        artists=("Holst",),
        duration_ms=1000,
        sample_rate=CD_SAMPLE_RATE,
        bit_depth=depth,
    )


def mixed() -> Album:
    """A FLAC then an MP3, which is how a lossy song arrives mid-album."""
    return Album(
        identity=AlbumIdentity(album_artist="Holst", title="The Planets"),
        tracks=(song(1, "flac", STATED_DEPTH), song(2, "mp3", NO_DEPTH)),
    )


def played(made: MainWindow, row: int) -> None:
    """Start the song at that row and let the window catch up with it."""
    album_row = made._model.index(0, 0)
    made.activate(made._model.index(row, 0, album_row))
    made._poll_transport()


def switch(made: MainWindow):
    """The control itself."""
    return made._bottom_tray.sound.exclusive_button


def over_mixed(made: MainWindow, player: RecordingPlayer) -> MainWindow:
    """The window over the mixed album, with a device answering as the real one.

    The real output modules open the mixer for a lossy file with the file's
    reason, whatever the device could do; the stand-in is told to do the same.
    """
    made._model.set_albums((mixed(),))
    player.grants = False
    player.refusal = NO_STATED_DEPTH
    return made


def test_a_lossy_song_stands_the_switch_down(
    window: MainWindow, player: RecordingPlayer
) -> None:
    made = over_mixed(window, player)
    played(made, LOSSY_ROW)
    assert not switch(made).isEnabled()
    assert switch(made).toolTip() == LOSSY_TOOLTIP


def test_it_wears_the_red_rounded_rectangle(
    window: MainWindow, player: RecordingPlayer
) -> None:
    made = over_mixed(window, player)
    played(made, LOSSY_ROW)
    danger = QColor(palette_for(made.theme_mode).danger).name()
    assert wears_the_dead_ring(switch(made), danger)


def test_the_choice_outlives_the_lossy_song(
    window: MainWindow, player: RecordingPlayer
) -> None:
    """The defect this replaces: one MP3 used to throw the choice away."""
    made = over_mixed(window, player)
    made.toggle_exclusive()
    played(made, LOSSY_ROW)
    assert made._transport.output_mode is OutputMode.EXCLUSIVE
    assert made._settings.get_setting(SETTING_OUTPUT_MODE) == (
        OutputMode.EXCLUSIVE.value
    )


def test_nothing_is_blamed_on_the_rate(
    window: MainWindow, player: RecordingPlayer
) -> None:
    """The status line once said the device takes the very rate it refused."""
    made = over_mixed(window, player)
    made.toggle_exclusive()
    played(made, LOSSY_ROW)
    assert "refused" not in made.statusBar().currentMessage()


def test_a_lossless_song_after_it_plays_exclusively_again(
    window: MainWindow, player: RecordingPlayer
) -> None:
    """No press needed: the choice stood the whole time."""
    made = over_mixed(window, player)
    made.toggle_exclusive()
    played(made, LOSSY_ROW)
    player.grants = True
    played(made, LOSSLESS_ROW)
    assert switch(made).isEnabled()
    assert switch(made).toolTip() == SHARED_TOOLTIP
    assert player.report.mode is OutputMode.EXCLUSIVE


def test_the_struck_artwork_comes_back_with_it(
    window: MainWindow, player: RecordingPlayer
) -> None:
    """The picture still says what a press would do: give the device back."""
    made = over_mixed(window, player)
    made.toggle_exclusive()
    struck = switch(made).icon().pixmap(32).toImage()
    played(made, LOSSY_ROW)
    player.grants = True
    played(made, LOSSLESS_ROW)
    assert switch(made).icon().pixmap(32).toImage() == struck


def test_a_listener_who_never_chose_it_gets_it_back_unchosen(
    window: MainWindow, player: RecordingPlayer
) -> None:
    """Enabled again, showing shared: the press is still theirs to make."""
    made = over_mixed(window, player)
    played(made, LOSSY_ROW)
    played(made, LOSSLESS_ROW)
    assert switch(made).isEnabled()
    assert switch(made).toolTip() == EXCLUSIVE_TOOLTIP
    assert made._transport.output_mode is OutputMode.SHARED


def test_a_lossless_song_is_offered_it_to_begin_with(
    window: MainWindow, player: RecordingPlayer
) -> None:
    """Guard the guard: standing it down for every song would pass above."""
    made = over_mixed(window, player)
    played(made, LOSSLESS_ROW)
    assert switch(made).isEnabled()


def test_a_platform_stand_down_is_not_undone_by_a_lossless_song(
    application: QApplication,
) -> None:
    """Where the platform offers no route, no song brings the switch back."""
    store = BareStore()

    def session():
        return ScanLibrary(None, None, None, store), store

    made = MainWindow(
        scan_session=session,
        loader=LoadLibrary(store),
        transport=Transport(RecordingPlayer()),
        settings=store,
        exclusive_refusal=PLATFORM_REFUSAL,
    )
    made._model.set_albums((mixed(),))
    made.restore_switches()
    played(made, LOSSY_ROW)
    played(made, LOSSLESS_ROW)
    assert not switch(made).isEnabled()
    assert switch(made).toolTip() == PLATFORM_REFUSAL
