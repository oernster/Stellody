"""The transport's switches: volume, mute, shuffle, repeat and the equaliser.

Split out of `playing.py` on 2026-09-13, when marking the track in hand needed
room in a module already inside the danger band. The seam is a real one: each
of these is a setting the listener leaves somewhere, applied then remembered,
where what is left over there is pressing the transport and showing its state.
"""

from __future__ import annotations

from PySide6.QtCore import Slot

from stellody.domain.equalising import Equalisation, as_text, from_text
from stellody.domain.playback import RepeatMode
from stellody.ui.settings_keys import (
    FALSE,
    SETTING_EQ_ENABLED,
    SETTING_EQ_GAINS,
    SETTING_MUTED,
    SETTING_REPEAT,
    SETTING_SHUFFLE,
    SETTING_VOLUME,
    TRUE,
)
from stellody.ui.volume import DEFAULT_PERCENT, MAXIMUM_PERCENT, MINIMUM_PERCENT


class Switches:
    """The window's switches, each set, shown and remembered together."""

    @Slot(int)
    def set_volume(self, percent: int) -> None:
        """Take the slider's whole percent down to the gain the engine wants.

        Stored as percent because that is what the user set and what the
        tooltip says; the fraction is the engine's business and the conversion
        happens once, here.
        """
        self._transport.set_volume(percent / MAXIMUM_PERCENT)
        self._bottom_tray.set_percent(percent)
        self._settings.set_setting(SETTING_VOLUME, str(percent))

    def restore_volume(self) -> None:
        """Start at the volume last chosen, at the default when none has been.

        A stored value that cannot be read as a number falls back to the same
        default rather than to silence or to full: both of those are a worse
        surprise than the level a first run would have used.
        """
        stored = self._settings.get_setting(SETTING_VOLUME, str(DEFAULT_PERCENT))
        try:
            percent = int(stored)
        except ValueError:
            percent = DEFAULT_PERCENT
        self.set_volume(min(max(MINIMUM_PERCENT, percent), MAXIMUM_PERCENT))

    def restore_switches(self) -> None:
        """Bring mute, shuffle and repeat back as they were last left.

        A switch that forgets itself between sessions is a switch the listener
        has to set every time, which is the same as not having it.
        """
        self._apply_muted(self._flag(SETTING_MUTED))
        self._apply_shuffled(self._flag(SETTING_SHUFFLE))
        self._apply_repeat(self._stored_repeat())
        self._transport.set_equalisation(self._stored_equalisation())

    def _stored_equalisation(self) -> Equalisation:
        """The curve last left, flat where nothing readable is stored."""
        return from_text(
            self._settings.get_setting(SETTING_EQ_GAINS, ""),
            self._flag(SETTING_EQ_ENABLED),
        )

    def set_equalisation(self, equalisation: Equalisation) -> None:
        """Apply the curve and remember it, which go together."""
        self._transport.set_equalisation(equalisation)
        self._settings.set_setting(SETTING_EQ_GAINS, as_text(equalisation))
        self._remember(SETTING_EQ_ENABLED, equalisation.enabled)

    def toggle_mute(self) -> None:
        """Silence the output, else give it back at the level already chosen."""
        self._apply_muted(not self._transport.muted)

    def toggle_shuffle(self) -> None:
        """Scatter the queue, else put the album back into its own order."""
        self._apply_shuffled(not self._transport.shuffled)

    def toggle_repeat(self) -> None:
        """Step the switch on: off, then the album, then one track, then off."""
        self._apply_repeat(self._transport.repeat.after)

    def _apply_muted(self, muted: bool) -> None:
        """Set the switch, show it and remember it: the three go together."""
        self._transport.set_muted(muted)
        self._bottom_tray.set_muted(muted)
        self._remember(SETTING_MUTED, muted)

    def _apply_shuffled(self, shuffled: bool) -> None:
        """Set the switch, show it and remember it."""
        self._transport.set_shuffled(shuffled)
        self._bottom_tray.set_shuffled(shuffled)
        self._remember(SETTING_SHUFFLE, shuffled)

    def _apply_repeat(self, repeat: RepeatMode) -> None:
        """Set the switch, show it and remember it: the three go together."""
        self._transport.set_repeat(repeat)
        self._bottom_tray.set_repeat(repeat)
        self._settings.set_setting(SETTING_REPEAT, repeat.value)

    def _stored_repeat(self) -> RepeatMode:
        """The mode last left, reading the boolean this setting used to hold.

        Before there were three states it held Stellody's own true or false.
        An upgrade therefore finds a boolean here; the switch belongs where
        the listener left it rather than quietly back at off. Anything
        else unreadable is off, which is the state that surprises nobody.
        """
        stored = self._settings.get_setting(SETTING_REPEAT, RepeatMode.OFF.value)
        if stored == TRUE:
            return RepeatMode.ALBUM
        try:
            return RepeatMode(stored)
        except ValueError:
            return RepeatMode.OFF

    def _remember(self, key: str, on: bool) -> None:
        """Store one switch under the name it is read back by."""
        self._settings.set_setting(key, TRUE if on else FALSE)
