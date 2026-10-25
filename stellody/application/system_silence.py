"""Noticing that the system's own mixer is holding Stellody silent. FR-O21.

Found on 2026-10-25 after hours spent looking in the wrong place: Windows had
the installed Stellody at nought in its Volume mixer, so every track played
nothing while the visualiser moved; nothing Stellody showed said why. The
level is the listener's and Stellody never changes it (Oliver's ruling); it
says so instead.

Asked once each time music starts, a track opened or one resumed, rather than
on every poll: the answer comes from walking the system's audio sessions.
A level put right part way through needs no one telling.

Mixed into the transport beside `OutputChoosing`.
"""

from __future__ import annotations

from collections.abc import Callable

from stellody.domain.playback import SystemVolume

# How the system's mixer holds Stellody's sound; None where it cannot say.
SystemVolumeReader = Callable[[], SystemVolume | None]


def nothing_known() -> SystemVolume | None:
    """The reader for a platform with no such setting: it claims nothing."""
    return None


class SystemSilence:
    """Asks after each start whether the system is silencing the music."""

    _system_volume: SystemVolumeReader
    _volume_unasked: bool
    # The transport's own answer to whether sound is being produced.
    playing: bool

    def _ask_about_volume(self) -> None:
        """Music is starting: ask the system once it is under way."""
        self._volume_unasked = True

    def take_system_silence(self) -> SystemVolume | None:
        """What is silencing the music just started, once; None if nothing.

        Waits for the music to be playing, since the system holds a session
        only while there is a stream running to hold.
        """
        if not (self._volume_unasked and self.playing):
            return None
        self._volume_unasked = False
        volume = self._system_volume()
        if volume is None or not volume.silences:
            return None
        return volume
