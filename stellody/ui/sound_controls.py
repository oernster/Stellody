"""The controls saying how the music sounds: volume, mute, exclusive, equalizer.

They sit together at the right end of the bottom strip, ahead of shuffle and
repeat, because every one of them acts on what comes out of the speakers
rather than on what the library holds or which track is next. Volume sits
immediately left of mute because the two are one thought: how loud, then
whether at all.

A rule then stands between those two and the last pair, because the question
changes. Volume and mute are about the level; the output mode and the
equalizer are about the stream itself, one asking for the device untouched and
the other shaping what is sent to it. Oliver asked for the order on
2026-09-17: volume, mute, the rule, exclusive output, the equalizer.

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
from PySide6.QtWidgets import QFrame, QHBoxLayout, QPushButton, QWidget

from stellody.shared import resources
from stellody.ui.icons import plain_icon, struck_through
from stellody.ui.tray_parts import icon_button, separator
from stellody.ui.volume import DEFAULT_PERCENT, VolumeSlider

EQUALISER_TOOLTIP = "Shape what is heard"
MUTE_TOOLTIP = "Mute"
UNMUTE_TOOLTIP = "Unmute"
# What a press would move TO, as every switch here is worded. Exclusive
# output asks the device for the track's own rate with nothing in the way;
# shared output goes through the system mixer, which always opens.
EXCLUSIVE_TOOLTIP = "Take the device exclusively, for the track untouched"
SHARED_TOOLTIP = "Go back to sharing the device with everything else"
# The rule between the level and the stream. The width and the height are the
# tray's, handed in with the buttons' own sizes.
SEPARATOR_WIDTH_PX = 1


class SoundControls(QWidget):
    """Volume, mute, the rule, the output mode and the equalizer, in order."""

    def __init__(
        self,
        parent: QWidget,
        button_px: int,
        icon_px: int,
        gap_px: int,
        toggle_mute: Callable[[], None] = lambda: None,
        set_volume: Callable[[int], None] = lambda _percent: None,
        open_equaliser: Callable[[], None] = lambda: None,
        toggle_exclusive: Callable[[], None] = lambda: None,
        separator_height_px: int = 0,
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
        self.stream_separator = separator(
            self, SEPARATOR_WIDTH_PX, separator_height_px or icon_px
        )
        self.exclusive_button = icon_button(
            self,
            resources.exclusive_icon_path(),
            EXCLUSIVE_TOOLTIP,
            toggle_exclusive,
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
        for part in self.parts():
            row.addWidget(part)

    def parts(self) -> tuple[QWidget, ...]:
        """Everything drawn here, left to right, the rule included."""
        return (
            self.volume_button,
            self.mute_button,
            self.stream_separator,
            self.exclusive_button,
            self.equaliser_button,
        )

    def stops(self) -> tuple[QPushButton, ...]:
        """The controls the ring stops at, left to right as they are drawn.

        The rule is not one of them: it is a line, so it takes no focus and
        `parts` is what the layout is built from instead.
        """
        return tuple(part for part in self.parts() if not isinstance(part, QFrame))

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

    def set_exclusive(self, exclusive: bool) -> None:
        """Show what a press would do, as every switch in this application does.

        Plain artwork while the device is shared, because that press takes it;
        struck through while it is held exclusively, because that press gives
        it back. It says what was ASKED for rather than what the device
        granted: a device that refuses is answered with the shared stream and
        the position bar says so, while the choice stands and the next track
        asks again.
        """
        artwork = resources.exclusive_icon_path()
        self.exclusive_button.setIcon(
            struck_through(artwork, resources.negative_icon_path(), self._icon_px)
            if exclusive
            else plain_icon(artwork)
        )
        self.exclusive_button.setToolTip(
            SHARED_TOOLTIP if exclusive else EXCLUSIVE_TOOLTIP
        )

    def refuse_exclusive(self, reason: str) -> None:
        """Say the platform has no route past its mixer, then stand down.

        A control that cannot do anything is worse than no control, so it is
        disabled rather than left to be pressed; the reason is in the tooltip,
        because a disabled button with no explanation reads as a fault.
        """
        self.exclusive_button.setEnabled(False)
        self.exclusive_button.setToolTip(reason)

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
