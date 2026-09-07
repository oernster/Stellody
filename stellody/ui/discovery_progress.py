"""The two discovery bars in the tray, left of the button that starts a run.

**Two bars rather than one, one for each half of a run.** Ruled on 2026-09-07.
A run has two stages that measure different things: the first asks what each
artist in the ticked genres released, the second asks what the candidates that
turned up play. One bar carrying both in turn tells you how far through the
current half you are and nothing at all about the other, so a bar back at a
tenth is either terrible news or ordinary progress and there is no way to know
which. Stacked, the pair says where the run is: the first full and the second
climbing is plainly further along than the first climbing and the second empty.

**They are always there.** A control that appeared when a run started would
move every button beside it. The tray centres the transport between two
stretches, so the whole middle of the window would jump at the moment somebody
pressed Find. The slot is reserved instead: at rest both bars are empty and
each carries its own name, which also answers what the space is doing there.

**Each says its stage rather than the artist.** A run names artists like
"Jools Holland & His Rhythm & Blues Orchestra", which no strip of a toolbar is
going to hold. Each bar carries its stage and its percentage, both of which
fit; the name goes in the tooltip, where there is room for it.

**How long is left is written at the RIGHT END of whichever bar is moving.**
The status bar says it in a sentence, which is where FR-D35 put it and where it
stays. The trouble reported on 2026-09-07 is that the sentence sits at the foot
of a window whose bars are at the top, so somebody watching a percentage never
meets it. Both places, then, rather than one or the other.

**The two pieces of writing on a bar are laid out rather than left to
collide.** The strip is 170 pixels and the middle of it is nearly full at
"Looking up 50%", so a second piece of text that merely hoped for room would
sit on top of the first in whatever font the machine happens to use. The room
the time needs is taken out first; the stage name is then centred in what is
left, elided where even that does not hold it. Qt draws one string per bar, so
both are drawn here and the bar's own text is turned off.

**A bar is not a control.** It takes no focus and the keyboard ring steps over
it, exactly as it steps over a separator.
"""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import Property, QRect, Qt
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QProgressBar, QVBoxLayout, QWidget

from stellody.application.values import PERCENT, DiscoveryProgress, DiscoveryStage

# What the pair says it is for while nothing is under way. On the slot rather
# than on either bar, since each bar's own writing is its stage.
RESTING = "Music discovery"
# What each half of a run is called where somebody can see it. Short enough to
# sit beside a percentage in a strip this narrow.
STAGE_NAMES = {
    DiscoveryStage.LOOKING_UP: "Looking up",
    DiscoveryStage.NARROWING: "Checking styles",
}
# The order they happen in, which is the order they are stacked in.
STAGE_ORDER = (DiscoveryStage.LOOKING_UP, DiscoveryStage.NARROWING)
# Named against the artist rather than the count, since the count is already
# drawn and the name is the thing that will not fit.
LOOKING_AT = "{stage}: {artist} ({done} of {total})"
# Wide enough for the longest stage name beside a percentage without the text
# being elided, narrow enough to leave the transport where it was.
BAR_WIDTH_PX = 170
# Between the two bars. Enough that they read as two, small enough that the
# pair still fills the height one bar used to have.
STACK_GAP_PX = 5
# Kept off the ends of a bar, so neither piece of writing sits against the
# groove's own border.
WRITING_PAD_PX = 6
# Between the two pieces of writing, so a centred stage name cannot end exactly
# where the time begins.
WRITING_GAP_PX = 4
NOTHING = ""
HALF = 2


def stacked_height(height_px: int) -> int:
    """How tall each bar is when two of them fill the slot one used to."""
    return (height_px - STACK_GAP_PX) // HALF


@dataclass(frozen=True, slots=True)
class Writing:
    """What a bar draws and where, worked out before anything is painted.

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


class StageBar(QProgressBar):
    """One half of a run: how far through it, under the name of that half."""

    def __init__(self, parent: QWidget, label: str, height_px: int) -> None:
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
        self.label = label
        self._brief = NOTHING
        self._started = False
        self._writing_colour = NOTHING
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

    @property
    def wanted(self) -> str:
        """What this bar means to say: its name, plus a number once it has one.

        A stage that has not begun shows no percentage at all. Nought per cent
        and not started look the same on a bar; they do not read the same in
        words, where the second is what an untouched half of a run is.
        """
        if not self._started:
            return self.label
        return f"{self.label} {self.value()}%"

    def rest(self) -> None:
        """Back to naming itself, with nothing under way."""
        self.setValue(0)
        self._brief = NOTHING
        self._started = False
        self.update()

    def show_percent(self, percent: int, brief: str = NOTHING) -> None:
        """How far through this half the run is, plus what the run has left.

        The time is handed in rather than worked out here: what to say about a
        pace belongs to the estimate, while this is a strip of a toolbar that
        draws what it is given.
        """
        self.setValue(percent)
        self._brief = brief
        self._started = True
        self.update()

    def finish(self) -> None:
        """Left full, because the run has moved on to the other half.

        The whole point of two bars: a stage that is done stays visibly done
        rather than being wound back to make room for the next one.
        """
        self.show_percent(PERCENT)

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
        wanted = self.wanted
        middle = metrics.elidedText(
            wanted, Qt.TextElideMode.ElideRight, middle_at.width()
        )
        return Writing(wanted, middle, middle_at, self._brief, brief_at)

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


class DiscoveryBars(QWidget):
    """Both halves of a run, stacked in the slot one bar used to hold.

    The window talks to this rather than to either bar: what it has is a report
    naming a stage; which bar that means is this widget's business.
    """

    def __init__(self, parent: QWidget, height_px: int) -> None:
        super().__init__(parent)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setFixedSize(BAR_WIDTH_PX, height_px)
        each = stacked_height(height_px)
        self.bars = {
            stage: StageBar(self, STAGE_NAMES[stage], each) for stage in STAGE_ORDER
        }
        stack = QVBoxLayout(self)
        stack.setContentsMargins(0, 0, 0, 0)
        stack.setSpacing(STACK_GAP_PX)
        for stage in STAGE_ORDER:
            stack.addWidget(self.bars[stage])
        self.rest()

    @property
    def looking_up(self) -> StageBar:
        """The first half: what each artist in the ticked genres released."""
        return self.bars[DiscoveryStage.LOOKING_UP]

    @property
    def checking_styles(self) -> StageBar:
        """The second half: what the candidates that turned up play."""
        return self.bars[DiscoveryStage.NARROWING]

    @property
    def resting(self) -> bool:
        """True where no run has reported to either bar."""
        return all(bar.wanted == bar.label for bar in self.bars.values())

    def rest(self) -> None:
        """Say what the space is for, with nothing under way."""
        for bar in self.bars.values():
            bar.rest()
        self._say(RESTING)

    def show_progress(self, progress: DiscoveryProgress, brief: str = NOTHING) -> None:
        """Draw this report on the bar for the stage it came from.

        Every earlier stage is left full rather than untouched: a report from
        the second half is itself the news that the first half finished, since
        the run does not announce the ending of one stage separately.
        """
        for stage in STAGE_ORDER[: STAGE_ORDER.index(progress.stage)]:
            self.bars[stage].finish()
        self.bars[progress.stage].show_percent(progress.percent, brief)
        self._say(
            LOOKING_AT.format(
                stage=STAGE_NAMES[progress.stage],
                artist=progress.artist,
                done=progress.done + 1,
                total=progress.total,
            )
        )

    def _say(self, words: str) -> None:
        """One tooltip over the whole slot, bars included.

        Set on the children as well as on the pair: a tooltip belongs to the
        widget under the pointer, which is almost always a bar rather than the
        few pixels of gap between them.
        """
        self.setToolTip(words)
        for bar in self.bars.values():
            bar.setToolTip(words)
