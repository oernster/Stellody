"""Pausing when the system moves its sound output, then carrying on there.

Asked for by Oliver on 2026-09-14, after a track went on playing through the
speakers once his headphones had connected. A stream is opened on one device
and stays on it, so music already playing cannot follow a new default by
itself. Rather than move it without warning, the music is paused where it is.
The listener decides when to carry on; the press that does it opens the track
again wherever the output is by then, at the place it was paused.

A pause the listener made themselves resumes exactly as before, on the stream
already open. Only a move of the output reopens.
"""

from __future__ import annotations

from stellody.application.playback_ports import PlaybackPort
from stellody.domain.outputs import OutputDevice
from stellody.domain.playback import PlaybackState


class OutputFollowing:
    """What a move of the system's output does to a transport. Mixed into it."""

    _player: PlaybackPort
    _held: bool
    _output_moved: bool
    _in_use: OutputDevice | None

    def output_moved(self) -> bool:
        """Pause for a move of the output; True when that stopped the music.

        A loaded track is marked whether it was playing or not, since a paused
        one is still open on the device that has just been left. With nothing
        loaded there is nothing to mark: the next track is opened where the
        output now is.

        Music on a device the listener named is not on the default, so the
        default moving is nothing to it (`OUTPUTS.md`, Amendment 3).
        """
        if self._in_use is not None:
            return False
        state = self._player.state
        if not state.is_active:
            return False
        already = self._output_moved
        self._output_moved = True
        # The device went away beneath the stream before this report came:
        # measured 2026-09-19, the write fails 0.29 s ahead of Qt. The engine
        # has already held the track, so this move is what stopped the music.
        if self._player.interrupted:
            self._held = True
            return not already
        if state is not PlaybackState.PLAYING:
            return False
        self._held = True
        self._player.pause()
        return True

    def _reopen_where_paused(self) -> None:
        """Open the track in hand again where the output now is, then play on.

        It carries on from what was last HEARD rather than from the decode,
        which runs a block ahead: the block in hand at the pause was never
        written, so starting from the decode would skip it. The device is
        sought directly rather than through `seek`, which adds the lead a
        stream with audio already queued needs; a stream just opened has none.
        """
        heard = self.position
        self._load_current(playing=False, waiting=False)
        if heard is not None:
            self._player.seek(heard.frame)
        self._held = False
        self._player.play()
