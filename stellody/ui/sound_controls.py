"""The three controls saying how the music sounds: volume, mute, the equalizer.

They sit together at the right end of the bottom strip, ahead of shuffle and
repeat, because all three act on what comes out of the speakers rather than on
what the library holds or which track is next. Volume sits immediately left of
mute because the two are one thought: how loud, then whether at all. The
equalizer follows them, since it shapes the same sound the two before it set
the level of.

A group of its own rather than three loose buttons on the strip, so the order is
stated once and the strip delegates to it, as it does for what the library is
shown as. The slider the volume button opens lives in `volume.py`, so the button
can sit wherever it reads best without the slider following it around; it
opens above the button where there is room, which on the bottom strip is always.

Every picture here says what a press would DO: the mute switch is struck
through while the sound is on, because that press is the one that silences it.
"""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QPushButton, QWidget

from stellody.shared import resources
from stellody.ui.icons import plain_icon, struck_through
from stellody.ui.tray_parts import icon_button
from stellody.ui.volume import DEFAULT_PERCENT, VolumeSlider

EQUALISER_TOOLTIP = "Shape what is heard"
MUTE_TOOLTIP = "Mute"
UNMUTE_TOOLTIP = "Unmute"


class SoundControls(QWidget):
    """The volume, the mute switch and the equalizer, in that order."""

    def __init__(
        self,
        parent: QWidget,
        button_px: int,
        icon_px: int,
        gap_px: int,
        toggle_mute: Callable[[], None] = lambda: None,
        set_volume: Callable[[int], None] = lambda _percent: None,
        open_equaliser: Callable[[], None] = lambda: None,
    ) -> None:
        super().__init__(parent)
        # A container is never a stop, so it is said rather than assumed.
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._icon_px = icon_px
        self.volume_button = icon_button(
            self, resources.volume_icon_path(), "Volume", self._open, button_px, icon_px
        )
        self._popup = VolumeSlider(self, set_volume)
        self._percent = DEFAULT_PERCENT
        self.mute_button = icon_button(
            self,
            resources.unmute_icon_path(),
            MUTE_TOOLTIP,
            toggle_mute,
            button_px,
            icon_px,
        )
        self.equaliser_button = icon_button(
            self,
            resources.equaliser_icon_path(),
            EQUALISER_TOOLTIP,
            open_equaliser,
            button_px,
            icon_px,
        )
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(gap_px)
        for button in self.stops():
            row.addWidget(button)

    def stops(self) -> tuple[QPushButton, ...]:
        """These controls, left to right as they are drawn."""
        return (self.volume_button, self.mute_button, self.equaliser_button)

    def set_percent(self, percent: int) -> None:
        """Remember where the volume is, so the slider opens showing it."""
        self._percent = percent
        self.volume_button.setToolTip(f"Volume {percent}%")

    def _open(self) -> None:
        """Put the slider up; take it down when it is already up."""
        if self._popup.isVisible():
            self._popup.hide()
            return
        if self._popup.dismissed_by(self.volume_button):
            return
        self._popup.open_at(self._percent, self.volume_button)

    def set_muted(self, muted: bool) -> None:
        """Show what a press would do, as every switch in this application does.

        A struck speaker while the sound is on says a press silences it; a
        plain one while it is off says a press brings it back. The tooltip says
        the same thing in words, so the two agree rather than each carrying
        half of it.
        """
        speaker = resources.unmute_icon_path()
        self.mute_button.setIcon(
            plain_icon(speaker)
            if muted
            else struck_through(speaker, resources.negative_icon_path(), self._icon_px)
        )
        self.mute_button.setToolTip(UNMUTE_TOOLTIP if muted else MUTE_TOOLTIP)
