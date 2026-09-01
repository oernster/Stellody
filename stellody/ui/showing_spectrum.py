"""The window's half of the visualiser: when it is on and when it is running.

Two different questions, kept apart. Whether the strip is SHOWN is the
listener's, answered from the Sound menu and remembered between sessions.
Whether it is RUNNING is the music's: a strip on show with nothing playing has
nothing to draw, so its timer is stopped and the measurement upstream with it.

Off costs nothing rather than little, which is the bargain the equalizer
already makes. Nothing is measured while the strip is hidden, nor while the
music is stopped, so a listener who never turns this on never pays for it
while one who leaves it on pays only during a record.
"""

from __future__ import annotations

from stellody.ui.settings_keys import SETTING_VISUALISER


class ShowingSpectrum:
    """The visualiser half of the window."""

    def restore_visualiser(self) -> None:
        """Bring the strip back as it was left, hidden when nothing is stored.

        Hidden is the default rather than shown: it is a thing to turn on, so
        a first run opens on the library rather than on a display of something
        that is not playing yet.
        """
        self._apply_visualiser(self._flag(SETTING_VISUALISER))

    def toggle_visualiser(self) -> None:
        """Show the strip, else take it away."""
        self._apply_visualiser(not self._visualiser.isVisible())

    def _apply_visualiser(self, on: bool) -> None:
        """Show it, measure for it and remember it: the three go together."""
        self._visualiser.setVisible(on)
        self._visualiser_action.setChecked(on)
        self._transport.set_visualising(on)
        self._remember(SETTING_VISUALISER, on)
        self.follow_spectrum()

    def follow_spectrum(self) -> None:
        """Run the strip while there is something for it to draw, else stop it.

        Asked on every transport change rather than on a timer of its own,
        because the answer only changes when what is playing does. Starting an
        already running strip is a no-op, so this is safe to call as often as
        the transport reports.
        """
        if self._visualiser.isVisible() and self._transport.playing:
            self._visualiser.start()
            return
        self._visualiser.stop()
