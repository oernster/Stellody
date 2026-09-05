"""Choosing an album's genres from the catalogue, several at once.

A grid of boxes rather than a line to type in, because a genre is chosen from
a settled list rather than invented: typing invites a third spelling of a name
the library already holds two of, which is the disagreement the tag editor
exists to end.

**Grouped, because the catalogue has two levels.** Each main category leads its
own group with its styles indented under it, so Trance is visibly a kind of
Electronic rather than a name beside it. The groups are dealt into columns by
height rather than in order, since Electronic carries eleven styles while four
mains carry none at all; a column-by-column fill would leave one column twice
the length of another.

**A style states its main, so the boxes say so as they are ticked.** Ticking a
style ticks its main; unticking a main unticks its styles. Without that the
panel would show Trance ticked and Electronic clear while the value it answers
with holds both, which is a panel disagreeing with itself.

It stands in for a line edit wherever the panel keeps one, answering `text()`
with the same kind of stored value a typed field gives. That is what lets the
album form hold one dictionary rather than two.
"""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from stellody.domain.genres import (
    CATALOGUE,
    GENRES,
    MAIN_OF,
    chosen_in,
    stated_as,
)
from stellody.ui.ringed_check import RingedCheckBox

# Three rather than two, measured again after the catalogue was reshaped and
# still three: its 33 boxes over two columns ask for a panel 829 pixels tall,
# which falls off a laptop screen. Three brings it to 723; a fourth costs 222
# more pixels of width and saves 28 of height, since Electronic's twelve boxes
# are the floor and no number of columns gets under them.
COLUMNS = 3
# How far a style sits in from the main it belongs to. Enough to read as
# beneath it rather than beside it, without pushing the longest name out of
# the dialog.
INDENT_PX = 18

HINT = "An album can carry several. What you tick replaces what it carries now."
# Said over the same boxes when they are asking rather than stating. Each tick
# widens what is on screen, which is the opposite of what ticking means when an
# album is being described, so the line says so before anything is ticked.
ASK_HINT = "Every tick adds to what is shown. A style shows that style alone."

# Said where the album's own tag names nothing in the catalogue, so the panel
# never silently drops what the file says while showing no box ticked.
UNMATCHED = "Currently tagged {value}, which is not one of these."
# Said where there is no tag to drop at all. Without it an empty grid means
# two different things and looks identical in both: nothing to show; something
# shown that could not be represented. Somebody reading it cannot
# tell whether Stellody found nothing or ignored what it found.
UNSTATED = "This album states no genre."


@dataclass(frozen=True, slots=True)
class Manner:
    """What a grid of these boxes is being used FOR.

    The same catalogue serves two questions and they differ in three places,
    all of them following from the one distinction: describing an album states
    what it is, while asking of the library states what to show.

    A style states its main when an album is described, since an album marked
    Trance IS electronic. It must NOT when the library is asked, since ticking
    Trance to have every kind of electronic music put in front of you is not
    what the tick said.
    """

    hint: str
    couples_mains: bool
    says_aside: bool


# Describing one album: ticking a style ticks its main; the line underneath
# says what the album carries when no box can hold it.
STATING = Manner(hint=HINT, couples_mains=True, says_aside=True)
# Asking the library: a tick is a question rather than a statement, so nothing
# is ticked on somebody's behalf and there is no album to say anything about.
ASKING = Manner(hint=ASK_HINT, couples_mains=False, says_aside=False)


def _mnemonic_safe(name: str) -> str:
    """A genre as Qt should draw it.

    Qt reads a single ampersand in a control's text as the marker before a
    shortcut key, so `Funk / Soul` would render with a stray underline and
    `Drum & Bass` as `Drum  Bass`. Doubling it is how one is asked for
    literally.
    """
    return name.replace("&", "&&")


def dealt_into_columns(
    catalogue: tuple[tuple[str, tuple[str, ...]], ...], columns: int
) -> tuple[tuple[tuple[str, tuple[str, ...]], ...], ...]:
    """The groups spread over that many columns, kept as even in height as
    they go.

    Each group goes to whichever column is shortest at the time, so the order
    within a column is still the catalogue's. Height is counted in boxes, one
    for the main plus one per style, since that is what the eye measures.
    """
    dealt: list[list[tuple[str, tuple[str, ...]]]] = [[] for _ in range(columns)]
    heights = [0] * columns
    for group in catalogue:
        into = heights.index(min(heights))
        dealt[into].append(group)
        heights[into] += 1 + len(group[1])
    return tuple(tuple(column) for column in dealt)


def _aside(stated: str, ticked: set[str]) -> str:
    """What the panel says under the boxes, which is nothing where all is well.

    Three states rather than two, because an empty grid is ambiguous: it means
    the album says nothing; or it means the album says something no box can
    hold. Silence in the first case reads as a defect, which is how this line
    came to be asked for.
    """
    if ticked:
        return ""
    return UNMATCHED.format(value=stated) if stated else UNSTATED


class GenreGrid(QWidget):
    """The catalogue as tick boxes, standing in for a line edit."""

    def __init__(
        self,
        value: str = "",
        parent: QWidget | None = None,
        manner: Manner = STATING,
    ) -> None:
        super().__init__(parent)
        self._manner = manner
        # A container is never a stop on the keyboard ring; the boxes are.
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.boxes: dict[str, RingedCheckBox] = {}
        ticked = set(chosen_in(value))

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        hint = QLabel(manner.hint, self)
        hint.setWordWrap(True)
        font = hint.font()
        font.setItalic(True)
        hint.setFont(font)
        outer.addWidget(hint)

        outer.addLayout(self._build_columns(ticked))

        said = _aside(value.strip(), ticked) if manner.says_aside else ""
        self.aside = QLabel(said, self)
        self.aside.setWordWrap(True)
        self.aside.setVisible(bool(self.aside.text()))
        outer.addWidget(self.aside)

    def _build_columns(self, ticked: set[str]) -> QHBoxLayout:
        """One column of groups beside another, each group a main and its own."""
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        for column in dealt_into_columns(CATALOGUE, COLUMNS):
            stack = QVBoxLayout()
            stack.setContentsMargins(0, 0, 0, 0)
            for main, styles in column:
                stack.addWidget(self._box(main, ticked))
                for style in styles:
                    indented = QHBoxLayout()
                    indented.setContentsMargins(0, 0, 0, 0)
                    indented.addSpacing(INDENT_PX)
                    indented.addWidget(self._box(style, ticked))
                    stack.addLayout(indented)
            stack.addStretch()
            row.addLayout(stack)
        return row

    def _box(self, name: str, ticked: set[str]) -> RingedCheckBox:
        """One tick box, remembered by the name it stands for."""
        box = RingedCheckBox(_mnemonic_safe(name), self)
        box.setChecked(name in ticked)
        box.toggled.connect(lambda on, which=name: self._agree_with(which, on))
        self.boxes[name] = box
        return box

    def _agree_with(self, name: str, on: bool) -> None:
        """Keep the ticks saying what the value they produce would say.

        Two rules and no more, both following from a style stating its main:
        ticking a style ticks that main; clearing a main clears its styles.
        The pair a listener would find surprising, clearing a style clearing
        its main, is deliberately absent: the album may still be electronic
        after they decide it is not specifically trance.

        Neither rule applies while the boxes are asking rather than stating:
        see `Manner`.
        """
        if not self._manner.couples_mains:
            return
        if on and name in MAIN_OF:
            self.boxes[MAIN_OF[name]].setChecked(True)
            return
        if not on:
            for style, main in MAIN_OF.items():
                if main == name:
                    self.boxes[style].setChecked(False)

    def chosen(self) -> tuple[str, ...]:
        """Every genre ticked, in catalogue order.

        Walked over the catalogue rather than over the boxes, since the boxes
        are built column by column and a column is not the catalogue's order.
        """
        return tuple(name for name in GENRES if self.boxes[name].isChecked())

    def text(self) -> str:
        """What is ticked, as the album form's other fields answer.

        Named to match a line edit rather than to describe itself, since the
        panel holds this beside them and asks all of them the same question.
        """
        return stated_as(self.chosen())
