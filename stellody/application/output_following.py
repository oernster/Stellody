"""Pausing when the system moves its sound output, then carrying on there.

Asked for by Oliver on 2026-09-14, after a track went on playing through the
speakers once his headphones had connected. A stream is opened on one device
and stays on it, so music already playing cannot follow a new default by
itself. Rather than move it without warning, the music is paused where it is.
The listener decides when to carry on; the press that does it opens the track
again wherever the output is by then, at the place it was paused.

A pause the listener made themselves resumes exactly as before, on the stream
already open. Only a move of the output reopens.

Ruled again by Oliver on 2026-09-19 (`OUTPUTS.md` FR-O15): a move to a
device that arrived, the one left still listed, carries the music on instead.
"""

from __future__ import annotations

from stellody.application.playback_ports import PlaybackPort
from stellody.domain.outputs import OutputChoice, OutputDevice
from stellody.domain.playback import PlaybackState


class OutputFollowing:
    """What a move of the system's output does to a transport. Mixed into it."""

    _player: PlaybackPort
    _held: bool
    _output_moved: bool
    _in_use: OutputDevice | None
    _choice: OutputChoice

    def output_switched(self) -> bool:
        """Carry the music to a new default; True when it paused instead.

        For a move that left the previous default still listed, which is a
        device arriving. While System default is the choice, the track in
        hand is opened there where it was: playing plays on, paused stays
        paused. A stream already interrupted lost its device, so its pause
        stands; music on the default only because the chosen device is away
        is never carried to one the listener did not choose (FR-O15).
        """
        if not self._choice.follows_default or self._player.interrupted:
            return self.output_moved()
        if self._player.state.is_active:
            self._reopen_in_place()
        return False

    def output_moved(self) -> bool:
        """Pause for a move of the output; True when that stopped the music.

        A loaded track is marked whether it was playing or not, since a paused
        one is still open on the device that has just been left. With nothing
        loaded there is nothing to mark: the next track is opened where the
        output now is.

        Music on a device the listener named is not on the default, so the
        default moving is nothing to it (`OUTPUTS.md` FR-O15).

        The track is held whatever the state, which is what ruled out a fall
        through at a track boundary. Found by the audit of 2026-10-03: a track
        that has played out reads as paused until the next poll moves the
        queue on, so a move landing then was let pass and the poll played the
        next track on the default. Holding it leaves the next track waiting
        for a press, as OQ-O5 rules (FR-O11).
        """
        if self._in_use is not None:
            return False
        state = self._player.state
        if not state.is_active:
            return False
        already = self._output_moved
        self._output_moved = True
        held = self._held
        self._held = True
        # The device went away beneath the stream before this report came:
        # measured 2026-09-19, the write fails 0.29 s ahead of Qt. The engine
        # has already held the track, so this move is what stopped the music.
        if self._player.interrupted:
            return not already
        if state is PlaybackState.PLAYING:
            self._player.pause()
            return True
        # Paused: by the listener, who already held it, else at the end of a
        # track, where this hold is what stops the next one starting.
        return not held

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
