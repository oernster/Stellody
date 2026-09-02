"""What the output sounds like, apart from which track is playing.

Volume, muting, the equalizer curve and whether anything is watching the
levels are one concern: they describe the stream rather than the queue, they
survive a track change untouched and none of them moves the music on. Kept
apart from the transport for that reason, as a mixin rather than a
collaborator because every one of them is a single line onto the port; a
wrapper object would add a hop and answer nothing new.
"""

from __future__ import annotations

from stellody.application.ports import PlaybackPort
from stellody.domain.equalising import Equalisation
from stellody.domain.playback import Loudness


class SoundSettings:
    """The output settings a transport carries. Mixed into `Transport`."""

    _player: PlaybackPort
    _loudness: Loudness
    _equalisation: Equalisation
    _visualising: bool

    def set_volume(self, level: float) -> None:
        """Set output gain, where 0.0 is silence and 1.0 is unattenuated."""
        self._loudness = self._loudness.at(level)
        self._player.set_volume(self._loudness.audible)

    @property
    def volume(self) -> float:
        """The gain chosen, whether or not it is currently being heard."""
        return self._loudness.level

    @property
    def muted(self) -> bool:
        """Whether output is held silent regardless of the level chosen."""
        return self._loudness.muted

    def set_muted(self, muted: bool) -> None:
        """Silence the output, else return it to the level already chosen."""
        self._loudness = self._loudness.silenced(muted)
        self._player.set_volume(self._loudness.audible)

    @property
    def equalisation(self) -> Equalisation:
        """The curve chosen, whether or not it is switched on."""
        return self._equalisation

    def set_equalisation(self, equalisation: Equalisation) -> None:
        """Choose the curve. Nothing already playing is disturbed."""
        self._equalisation = equalisation
        self._player.set_equalisation(equalisation)

    @property
    def levels(self) -> tuple[float, ...]:
        """The bands as the device last saw them, for whatever is drawing."""
        return self._player.levels

    def set_visualising(self, on: bool) -> None:
        """Say whether anything is watching, so nothing is measured for nobody."""
        self._visualising = on
        self._player.set_visualising(on)

    @property
    def visualising(self) -> bool:
        """Whether what goes out is being measured."""
        return self._visualising
