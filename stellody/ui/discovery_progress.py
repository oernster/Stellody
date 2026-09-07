"""The discovery bar that lives in the tray, left of the button that starts it.

**It is always there.** A control that appears when a run starts would move
every button beside it. The tray centres the transport between two stretches,
so the whole middle of the window would jump at the moment somebody pressed
Find. The slot is reserved instead: at rest the bar is empty and says
what it is for, which also answers what the space is doing there.

**It says the stage rather than the artist.** A run names artists like
"Jools Holland & His Rhythm & Blues Orchestra", which no strip of a toolbar is
going to hold. The bar carries the stage and the percentage, both of which fit;
the name goes in the tooltip, where there is room for it.

**How long is left is written at the RIGHT END, in the shortest words there
are.** The status bar says it in a sentence, which is where FR-D35 put it and
where it stays. The trouble reported on 2026-09-07 is that the sentence sits at
the foot of a window whose bar is at the top, so somebody watching the
percentage never meets it. Both places, then, rather than one or the other.

**The two pieces of writing are laid out rather than left to collide.** The
strip is 170 pixels and the middle of it is nearly full at "Looking up 50%", so
a second piece of text that merely hoped for room would sit on top of the first
in whatever font the machine happens to use. The room the time needs is taken
out first; the stage name is then centred in what is left, elided where even
that does not hold it. Qt draws one string per bar, so both are drawn here and
the bar's own text is turned off.

**A bar is not a control.** It takes no focus and the keyboard ring steps over
it, exactly as it steps over a separator.
"""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import Property, QRect, Qt
from PySide6.QtGui import QColor, QPainter
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
# being elided, narrow enough to leave the transport where it was.
BAR_WIDTH_PX = 170
# Kept off the ends of the bar, so neither piece of writing sits against the
# groove's own border.
WRITING_PAD_PX = 6
# Between the two pieces of writing, so a centred stage name cannot end exactly
# where the time begins.
WRITING_GAP_PX = 4


@dataclass(frozen=True, slots=True)
class Writing:
    """What the bar draws and where, worked out before anything is painted.

    Answered rather than merely drawn, so the layout can be asserted. A test
    reading pixels back off a widget would be measuring the platform's font
    rather than whether the two pieces of writing were kept apart.
    """

    # What the middle MEANS to say, against what of it fits. The two differ on
    # a narrow strip in a wide font; which happens is the machine's business
    # rather than this application's, so a test asserting the words has to read
    # `wanted`, else it is asserting the font the harness fell back to.
    wanted: str
    middle: str
    middle_at: QRect
    brief: str
    brief_at: QRect

    @property
    def shortened(self) -> bool:
        """True where what fits is less than what was meant."""
        return self.middle != self.wanted

    @property
    def collides(self) -> bool:
        """True where the two would be drawn over each other."""
        return bool(self.brief) and self.middle_at.intersects(self.brief_at)


class DiscoveryBar(QProgressBar):
    """How far a discovery run has got; what the space is for at rest."""

    def __init__(self, parent: QWidget, height_px: int) -> None:
        super().__init__(parent)
        self.setObjectName("DiscoveryBar")
        # A bar reports; it is never a stop and never wears a ring.
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setFixedSize(BAR_WIDTH_PX, height_px)
        # Qt draws one string, centred, across the whole bar. Two are wanted in
        # two places, so both are drawn below and Qt is told to draw neither.
        self.setTextVisible(False)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setRange(0, PERCENT)
        self._middle = RESTING
        self._brief = ""
        self._writing_colour = ""
        self.rest()

    def _read_writing(self) -> str:
        """The colour the stylesheet handed over; empty until it has."""
        return self._writing_colour

    def _write_writing(self, colour: str) -> None:
        """Take the colour from the stylesheet, then paint in it."""
        self._writing_colour = colour
        self.update()

    # Fed from the stylesheet, so the palette stays the one home for a colour.
    # The arrangement the ringed menu bar and the ringed checkbox already use,
    # for the same reason: what is painted here cannot be said in QSS.
    writingColour = Property(str, _read_writing, _write_writing)

    def rest(self) -> None:
        """Say what the space is for, with nothing under way."""
        self.setValue(0)
        self._middle = RESTING
        self._brief = ""
        self.setToolTip(RESTING)
        self.update()

    def show_progress(self, progress: DiscoveryProgress, brief: str = "") -> None:
        """Say how far along the run is, what it is at and how long is left.

        The time is handed in rather than worked out here: what to say about a
        pace belongs to the estimate, while this is a strip of a toolbar that
        draws what it is given.
        """
        stage = STAGE_NAMES[progress.stage]
        self.setValue(progress.percent)
        self._middle = f"{stage} {progress.percent}%"
        self._brief = brief
        self.setToolTip(
            LOOKING_AT.format(
                stage=stage,
                artist=progress.artist,
                done=progress.done + 1,
                total=progress.total,
            )
        )
        self.update()

    def writing(self) -> Writing:
        """What would be drawn and where, the time given its room first.

        The time is placed against the right edge; the stage name is centred in
        what is left rather than in the whole bar, so the two cannot meet
        however wide the machine's font draws either of them.
        """
        inside = self.contentsRect().adjusted(WRITING_PAD_PX, 0, -WRITING_PAD_PX, 0)
        metrics = self.fontMetrics()
        taken = metrics.horizontalAdvance(self._brief) if self._brief else 0
        brief_at = QRect(inside)
        brief_at.setLeft(inside.right() - taken)
        middle_at = QRect(inside)
        if taken:
            middle_at.setRight(brief_at.left() - WRITING_GAP_PX)
        middle = metrics.elidedText(
            self._middle, Qt.TextElideMode.ElideRight, middle_at.width()
        )
        return Writing(self._middle, middle, middle_at, self._brief, brief_at)

    def paintEvent(self, event) -> None:
        """Qt's own bar, then the two pieces of writing over what it drew."""
        super().paintEvent(event)
        drawn = self.writing()
        painter = QPainter(self)
        painter.setPen(QColor(self._writing_colour or self.palette().text().color()))
        painter.drawText(drawn.middle_at, Qt.AlignmentFlag.AlignCenter, drawn.middle)
        if drawn.brief:
            painter.drawText(
                drawn.brief_at,
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                drawn.brief,
            )
