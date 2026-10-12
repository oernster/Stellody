"""The window's half of the visualiser: it is always there, it runs with the music.

There is no switch. It was offered as one at first, from the Sound menu and
remembered between sessions, which asked a listener to decide about a few
centimetres of a strip they already have. Something that small and that cheap
should simply be there; a setting for it is a question nobody wanted asked.

What is left is the one question that has an answer worth having: whether there
is anything to draw. The repaint timer runs while the music does and stops when
it stops, so an idle window does no painting for a display of nothing. The
measuring upstream is switched on once in `start_watching` and left on.

Which STYLE it draws in is the listener's, chosen by name from the list the
button beside the view controls lifts (the same list sits under View); it is
remembered between sessions by
name as the sleeve size is. That is not the switch that was taken away:
nothing is asked, the strip is always there and a choice only changes how it
looks.
"""

from __future__ import annotations

from stellody.ui.settings_keys import SETTING_VISUALISATION
from stellody.ui.visualisations import (
    Visualisation,
    fill_styles,
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

    def show_visualisation(self, style: Visualisation) -> None:
        """Draw in this style, tick it in both lists and remember the choice.

        Both lists, the strip's and the View menu's, are filled afresh with
        each choice, so the tick moves in both whichever was used;
        `lift_menu.fill_choices` is safe to call from inside a line's own press.
        """
        self._visualiser.show_style(style)
        self._bottom_tray.show_visualisations(style, self.show_visualisation)
        fill_styles(self._style_menu, style, self.show_visualisation)
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
