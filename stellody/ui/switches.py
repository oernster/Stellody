"""The transport's switches: volume, mute, shuffle, repeat and the equaliser.

Split out of `playing.py` on 2026-09-13, when marking the track in hand needed
room in a module already inside the danger band. The seam is a real one: each
of these is a setting the listener leaves somewhere, applied then remembered,
where what is left over there is pressing the transport and showing its state.
"""

from __future__ import annotations

from PySide6.QtCore import Slot

from stellody.domain.equalising import Equalisation, as_text, from_text
from stellody.domain.playback import OutputMode, OutputReport, RepeatMode
from stellody.ui.settings_keys import (
    FALSE,
    SETTING_EQ_ENABLED,
    SETTING_EQ_GAINS,
    SETTING_MUTED,
    SETTING_OUTPUT_MODE,
    SETTING_REPEAT,
    SETTING_SHUFFLE,
    SETTING_VOLUME,
    TRUE,
    UNPLAYABLE_MESSAGE_MS,
)
from stellody.ui.stream_words import rate_text
from stellody.ui.volume import DEFAULT_PERCENT, MAXIMUM_PERCENT, MINIMUM_PERCENT

# Said once, in words, when a device turns exclusive output down. Oliver's
# point on 2026-09-18: a refusal a listener cannot act on makes the whole
# feature look broken rather than unsupported. So where the device has told us
# which rates it WILL take, the message names them beside the rate of the
# track that was refused, which between them say what to do about it.
REFUSAL_MESSAGE = "Exclusive output was refused, so the mixer is playing it: {reason}"
RATES_REFUSAL = (
    "Exclusive output was refused for this {track} track, so the mixer is "
    "playing it. This device takes exclusive output at {rates}."
)
NO_REASON_GIVEN = "the device did not say why"
# What a device that will take none at all is said to be. It stands the switch
# down exactly as an unsupported platform does, because the two are the same
# thing to a listener: there is no press that would achieve anything.
NO_RATES_AT_ALL = (
    "This sound device offers no exclusive output at any sample rate, so the "
    "music plays through the system mixer."
)
# What separates a list of rates. The last pair is joined by a word rather
# than a comma, since a list of numbers with no conjunction reads as one
# number typed badly.
RATE_SEPARATOR = ", "
LAST_RATE_SEPARATOR = " and "


def rates_text(rates: tuple[int, ...]) -> str:
    """A run of sample rates as a sentence names them.

    One rate reads as itself; two or more take a conjunction before the last,
    since "44.1 kHz, 48 kHz, 96 kHz" trails off where "44.1 kHz, 48 kHz and
    96 kHz" lands.
    """
    said = [rate_text(rate) for rate in rates]
    if len(said) == 1:
        return said[0]
    return RATE_SEPARATOR.join(said[:-1]) + LAST_RATE_SEPARATOR + said[-1]


class Switches:
    """The window's switches, each set, shown and remembered together."""

    def follow_output_refusal(self) -> None:
        """Take the switch back to shared where the device turned it down.

        Oliver's ruling on 2026-09-18: a refused mode must not leave the
        picture claiming it. The switch shows what is HAPPENING, so a device
        that said no takes it back to shared and says so along the status
        line, rather than sitting struck through over a mixer stream.

        It fires once. Standing down leaves the mode shared, so the next poll
        finds nothing to do; without that this would rewrite the status line
        four times a second for as long as the track lasted.

        The stream is left exactly as it is. A refused exclusive request was
        already opened through the mixer, so reopening it would buy a gap in
        the music and change nothing else.
        """
        if self._transport.output_mode is not OutputMode.EXCLUSIVE:
            return
        report = self._transport.report
        if report is None or not report.fell_back:
            return
        self._transport.stand_down_to_shared()
        self._bottom_tray.set_exclusive(False)
        self._settings.set_setting(SETTING_OUTPUT_MODE, OutputMode.SHARED.value)
        self.statusBar().showMessage(self._refusal_words(report), UNPLAYABLE_MESSAGE_MS)

    def _refusal_words(self, report: OutputReport) -> str:
        """What to say about a refusal, as usefully as the device allows.

        The device's own reason is the fallback rather than the first choice:
        "no exclusive format at this rate" is true and leaves a listener
        nowhere to go. Where the rates it does take can be had, they are what
        is said, since they are the thing that can be acted on.
        """
        rates = self._transport.exclusive_rates
        if not rates:
            return REFUSAL_MESSAGE.format(
                reason=report.fallback_reason or NO_REASON_GIVEN
            )
        return RATES_REFUSAL.format(
            track=rate_text(report.request.sample_rate),
            rates=rates_text(rates),
        )

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
        self.restore_output_mode()
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

    def toggle_exclusive(self) -> None:
        """Take the device exclusively, else go back to sharing it.

        Two states rather than a cycle, so the picture and the press are one
        thought: shared is where everything starts, since it is the mode no
        device refuses.
        """
        going = self._transport.output_mode is OutputMode.SHARED
        self._apply_output_mode(OutputMode.EXCLUSIVE if going else OutputMode.SHARED)

    def toggle_shuffle(self) -> None:
        """Scatter the queue, else put the album back into its own order."""
        self._apply_shuffled(not self._transport.shuffled)

    def toggle_repeat(self) -> None:
        """Step the switch on: off, then the album, then one track, then off."""
        self._apply_repeat(self._transport.repeat.after)

    def choose_repeat(self, repeat: RepeatMode) -> None:
        """Go straight to one mode, as the menu names them, without stepping."""
        self._apply_repeat(repeat)

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

    def _apply_output_mode(self, mode: OutputMode) -> None:
        """Set the mode, show it and remember it: the three go together.

        The transport reopens whatever is in hand on it, so the switch is
        heard rather than merely noted for the next track.
        """
        self._transport.set_output_mode(mode)
        self._bottom_tray.set_exclusive(mode is OutputMode.EXCLUSIVE)
        self._settings.set_setting(SETTING_OUTPUT_MODE, mode.value)

    def restore_output_mode(self) -> None:
        """Open on the mode last left, unless there is no choice to be had.

        Two ways there is none: a platform with no route past its own mixer;
        a device that will take no rate exclusively. They are one thing to
        a listener, since neither leaves a press that would achieve anything,
        so both stand the control down with the reason on it rather than
        leaving it pressable.

        What is WRITTEN DOWN is deliberately left alone in that case: a
        listener who chose exclusive output on one machine and opened the same
        settings on another finds it still chosen when they go back, rather
        than quietly reset by a machine that could not honour it.
        """
        refusal = self._exclusive_refusal or self._device_refusal()
        if refusal:
            self._transport.set_output_mode(OutputMode.SHARED)
            self._bottom_tray.refuse_exclusive(refusal)
            return
        self._apply_output_mode(self._stored_output_mode())

    def _device_refusal(self) -> str:
        """Why this DEVICE offers nothing, where it offers nothing at all.

        Empty where it offers something; empty too where the platform cannot
        be asked without disturbing whatever else is playing: an unanswered
        question is not a no, so nothing is stood down on one.
        """
        rates = self._transport.exclusive_rates
        return NO_RATES_AT_ALL if rates is not None and not rates else ""

    def _stored_output_mode(self) -> OutputMode:
        """The mode last left; shared where nothing readable is stored.

        Shared rather than the last thing written, for a value that is not a
        mode at all: a listener whose device is suddenly held exclusively by
        an application they did not ask to hold it has a silent machine and
        no idea why.
        """
        stored = self._settings.get_setting(
            SETTING_OUTPUT_MODE, OutputMode.SHARED.value
        )
        try:
            return OutputMode(stored)
        except ValueError:
            return OutputMode.SHARED

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
