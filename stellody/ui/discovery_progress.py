"""The discovery bar that lives in the tray, left of the button that starts it.

**It is always there.** A control that appears when a run starts would move
every button beside it, and the tray centres the transport between two
stretches, so the whole middle of the window would jump at the moment somebody
pressed Find. The slot is reserved instead: at rest the bar is empty and says
what it is for, which also answers what the space is doing there.

**It says the stage rather than the artist.** A run names artists like
"Jools Holland & His Rhythm & Blues Orchestra", which no strip of a toolbar is
going to hold. The bar carries the stage and the percentage, both of which fit;
the name goes in the tooltip, where there is room for it.

**A bar is not a control.** It takes no focus and the keyboard ring steps over
it, exactly as it steps over a separator.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QProgressBar, QWidget

from stellody.application.values import PERCENT, DiscoveryProgress, DiscoveryStage

RESTING = "Music discovery"
# What each half of a run is called where somebody can see it. Short enough to
# sit beside a percentage in a strip this narrow.
STAGE_NAMES = {
    DiscoveryStage.LOOKING_UP: "Looking up",
    DiscoveryStage.NARROWING: "Checking styles",
}
# Named against the artist rather than the count, since the count is already
# drawn and the name is the thing that will not fit.
LOOKING_AT = "{stage}: {artist} ({done} of {total})"
# Wide enough for the longest stage name beside a percentage without the text
# being elided, and narrow enough to leave the transport where it was.
BAR_WIDTH_PX = 170


class DiscoveryBar(QProgressBar):
    """How far a discovery run has got, or what the space is for at rest."""

    def __init__(self, parent: QWidget, height_px: int) -> None:
        super().__init__(parent)
        self.setObjectName("DiscoveryBar")
        # A bar reports; it is never a stop and never wears a ring.
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setFixedSize(BAR_WIDTH_PX, height_px)
        self.setTextVisible(True)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setRange(0, PERCENT)
        self.rest()

    def rest(self) -> None:
        """Say what the space is for, with nothing under way."""
        self.setValue(0)
        self.setFormat(RESTING)
        self.setToolTip(RESTING)

    def show_progress(self, progress: DiscoveryProgress) -> None:
        """Say how far along the run is, and what it is doing right now."""
        stage = STAGE_NAMES[progress.stage]
        self.setValue(progress.percent)
        self.setFormat(f"{stage} %p%")
        self.setToolTip(
            LOOKING_AT.format(
                stage=stage,
                artist=progress.artist,
                done=progress.done + 1,
                total=progress.total,
            )
        )
