"""The window's half of the visualiser: it is always there, it runs with the music.

There is no switch. It was offered as one at first, from the Sound menu and
remembered between sessions, which asked a listener to decide about a few
centimetres of a strip they already have. Something that small and that cheap
should simply be there; a setting for it is a question nobody wanted asked.

What is left is the one question that has an answer worth having: whether there
is anything to draw. The timer runs while the music does and stops when it
stops, taking the measurement upstream with it, so an idle window does no
arithmetic for a display of nothing.
"""

from __future__ import annotations


class ShowingSpectrum:
    """The visualiser half of the window."""

    def start_watching(self) -> None:
        """Measure what goes out, from now on.

        Said once, at the end of construction. Nothing turns it off again, so
        the only thing that stops the measuring is the music stopping.
        """
        self._transport.set_visualising(True)
        self.follow_spectrum()

    def follow_spectrum(self) -> None:
        """Run the display while there is something for it to draw, else stop it.

        Asked on every transport change rather than on a timer of its own,
        because the answer only changes when what is playing does. Starting an
        already running display is a no-op, so this is safe to call as often as
        the transport reports.
        """
        if self._transport.playing:
            self._visualiser.start()
            return
        self._visualiser.stop()
