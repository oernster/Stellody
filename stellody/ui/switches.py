"""The transport's switches: volume, mute, shuffle, repeat and the equaliser.

Split out of `playing.py` on 2026-09-13, when marking the track in hand needed
room in a module already inside the danger band. The seam is a real one: each
of these is a setting the listener leaves somewhere, applied then remembered,
where what is left over there is pressing the transport and showing its state.
"""

from __future__ import annotations

from PySide6.QtCore import Slot

from stellody.domain.equalising import Equalisation, as_text, from_text
from stellody.domain.playback import OutputMode, RepeatMode
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
from stellody.ui.sound_controls import LOSSY_TOOLTIP
from stellody.ui.stream_words import rate_text
from stellody.ui.volume import DEFAULT_PERCENT, MAXIMUM_PERCENT, MINIMUM_PERCENT

# Said once, in words, when a device turns down a request it was expected to
# take: another application holding it, say. A rate it does not list never gets
# this far, since such a song is not offered exclusive output at all.
REFUSAL_MESSAGE = "Exclusive output was refused, so the mixer is playing it: {reason}"
NO_REASON_GIVEN = "the device did not say why"
# Why a song the device cannot take at its own rate is not offered it: the
# rates it does take beside the song's own, which say what would work. Oliver's
# point on 2026-09-18: a refusal a listener cannot act on makes the whole
# feature look broken rather than unsupported.
RATE_NOT_TAKEN = (
    "Exclusive output is not offered for this song: this sound device takes "
    "it at {rates}, not at the song's {track}."
)
# Why a device fitting none of the library is not offered it while no song is in
# hand, ruled by Oliver on 2026-09-18: the wrong device is as misleading an
# offer as the wrong song.
NOT_FOR_THIS_LIBRARY = (
    "Exclusive output is not offered on this sound device: it takes it only at "
    "{rates}, where no lossless song in your library sits."
)
# What a device that will take none at all is said to be. It stands the switch
# down as an unsupported platform does, since there is no press that would
# achieve anything; unlike a platform, only until the output moves.
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

    def follow_song(self) -> None:
        """Offer exclusive output only for a song the device in use can take.

        Ruled by Oliver on 2026-09-18, for a lossy file first, then for a
        rate the device does not list: his Focal Bathys takes 48 kHz alone, so
        a 44.1 kHz song cannot have it there. Either way offering the switch
        would be a misleading hi-fi offer, so it stands down in the house red
        rounded rectangle with the reason in its tooltip rather than on the
        status line. The menu entry follows the switch.

        The CHOICE is left exactly as it was, also his ruling: the next song
        that can have exclusive output gets it with no press. Nothing is lost
        meanwhile, since a request the file or the device cannot honour is
        answered with the mixer and the readout says shared.
        """
        self._bottom_tray.hold_exclusive(self._not_offered())

    def _not_offered(self) -> str:
        """Why the song in hand cannot have exclusive output; empty where it can.

        The song in hand is the one loaded, else the one play would start,
        so a highlighted song is judged before it is pressed. An unanswered
        question about the device is not a no, so it stands nothing down.
        """
        rates = self._transport.exclusive_rates
        if rates is not None and not rates:
            return NO_RATES_AT_ALL
        track = self._transport.current or self._model.track_at(self.highlighted())
        if track is None:
            return self._not_for_the_library(rates)
        if not track.states_depth:
            return LOSSY_TOOLTIP
        if rates and track.sample_rate not in rates:
            return RATE_NOT_TAKEN.format(
                rates=rates_text(rates), track=rate_text(track.sample_rate)
            )
        return ""

    def _not_for_the_library(self, rates: tuple[int, ...] | None) -> str:
        """Why nothing the library holds could have it here; empty where some could.

        With no song in hand the device is judged against the library, ruled
        by Oliver on 2026-09-18: a device taking none of the rates its lossless
        songs are at is the wrong device; the right one brings the switch back.
        A library not yet loaded answers nothing, as does one holding nothing
        lossless, which stands nothing down.
        """
        held = self._library_rates
        if not rates or not held or held.intersection(rates):
            return ""
        return NOT_FOR_THIS_LIBRARY.format(rates=rates_text(rates))

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
        # A song that was never offered it is answered by `follow_song`, which
        # leaves the choice alone; only a refusal nobody could foresee moves it.
        if report is None or not report.fell_back or self._not_offered():
            return
        self._transport.stand_down_to_shared()
        self._bottom_tray.set_exclusive(False)
        self._settings.set_setting(SETTING_OUTPUT_MODE, OutputMode.SHARED.value)
        said = REFUSAL_MESSAGE.format(reason=report.fallback_reason or NO_REASON_GIVEN)
        self.statusBar().showMessage(said, UNPLAYABLE_MESSAGE_MS)

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
        """Open on the mode last left, unless the platform offers no choice.

        A platform with no route past its own mixer stands the control down
        for good, with the reason on it. A device is different: a move of the
        output can bring one that does take something, so what the device
        allows is judged song by song in `follow_song` instead.

        What is WRITTEN DOWN is deliberately left alone on such a platform: a
        listener who chose exclusive output on one machine and opened the same
        settings on another finds it still chosen when they go back, rather
        than quietly reset by a machine that could not honour it.
        """
        if self._exclusive_refusal:
            self._transport.set_output_mode(OutputMode.SHARED)
            self._bottom_tray.refuse_exclusive(self._exclusive_refusal)
            return
        self._apply_output_mode(self._stored_output_mode())
        self.follow_song()

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
