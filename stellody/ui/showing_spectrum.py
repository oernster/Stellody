"""The window's half of the visualiser: it is always there, it runs with the music.

There is no switch. It was offered as one at first, from the Sound menu and
remembered between sessions, which asked a listener to decide about a few
centimetres of a strip they already have. Something that small and that cheap
should simply be there; a setting for it is a question nobody wanted asked.

What is left is the one question that has an answer worth having: whether there
is anything to draw. The repaint timer runs while the music does and stops when
it stops, so an idle window does no painting for a display of nothing. The
measuring upstream is switched on once in `start_watching` and left on.

Which STYLE it draws in is the listener's, from the button beside the view
controls; it is remembered between sessions by name as the sleeve size is.
That is not the switch that was taken away: nothing is asked, the strip is
always there and a press only changes how it looks.
"""

from __future__ import annotations

from PySide6.QtCore import Slot

from stellody.ui.settings_keys import SETTING_VISUALISATION
from stellody.ui.visualisations import (
    Visualisation,
    next_visualisation,
    stored_visualisation,
)


class ShowingSpectrum:
    """The visualiser half of the window."""

    def start_watching(self) -> None:
        """Measure what goes out, from now on, in the style last chosen.

        Said once, at the end of construction. Nothing turns it off again, so
        the only thing that stops the measuring is the music stopping.
        """
        stored = self._settings.get_setting(SETTING_VISUALISATION, "")
        self.show_visualisation(stored_visualisation(stored))
        self._transport.set_visualising(True)
        self.follow_spectrum()

    @Slot()
    def cycle_visualisation(self) -> None:
        """Step the visualiser on to its next style, round to the first."""
        self.show_visualisation(next_visualisation(self._visualiser.style))

    def show_visualisation(self, style: Visualisation) -> None:
        """Draw in this style, say what is next and remember the choice."""
        self._visualiser.show_style(style)
        self._bottom_tray.set_next_visualisation(next_visualisation(style))
        self._settings.set_setting(SETTING_VISUALISATION, style.value)

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
