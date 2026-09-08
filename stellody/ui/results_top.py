"""The strip across the top of the results: the key, then what is being asked.

Split out of `results_dialog.py` on 2026-09-08, when ticking albums and taking
them to a shop needed room in a module already close to the cap. The seam is a
real one rather than a convenience: everything here explains the screen, while
what is left over there acts on it.

**The key.** Every row of the tree is a source artist, a candidate artist or an
album, so three lines say the whole of it. The circle carries the colour and
the words carry the meaning, which is the arrangement that still works in a
screenshot, for a reader who cannot separate the two hues and for anybody who
has simply not been told. FR-D39.

**The busy strip.** One lookup costs at least the gap the terms require and may
wait out two refusals, so several seconds of quiet is ordinary rather than a
fault. It holds its place while nothing is happening, carrying the instruction
instead: a strip that appeared would push the list down at the moment somebody
clicked an arrow in it. FR-D40.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QProgressBar, QVBoxLayout, QWidget

from stellody.application.values import PERCENT
from stellody.ui.results_words import (
    LEGEND_ALBUM,
    LEGEND_CANDIDATE,
    LEGEND_SOURCE,
    NOT_ASKING,
    asking_about,
)
from stellody.ui.theme import Palette

# The filled circle each line of the key is marked with, in the colour that
# line is about. One rich text label per line rather than a swatch beside a
# label, because Qt cannot align two widgets on a baseline.
MARK = "●"
KEY_LINE = '<span style="color: {colour}">{mark}</span>&nbsp; {words}'
# The key's own spacing, tighter than the gaps between parts of the dialog:
# three lines that belong together read as one block rather than as three.
KEY_GAP_PX = 2
# Tall enough to read as a strip rather than as a line, short enough that the
# list keeps the room. The same height a dialog button takes.
ASKING_BAR_PX = 28
APART_PX = 12


class ResultsTop(QWidget):
    """What the results dialog says about itself, above the list."""

    def __init__(self, colour: Palette, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        column = QVBoxLayout(self)
        column.setContentsMargins(0, 0, 0, 0)
        column.setSpacing(KEY_GAP_PX)
        self.key = tuple(
            self._key_line(shade, words)
            for shade, words in (
                (colour.source_artist, LEGEND_SOURCE),
                (colour.candidate_artist, LEGEND_CANDIDATE),
                (colour.text, LEGEND_ALBUM),
            )
        )
        for line in self.key:
            column.addWidget(line)
        column.addSpacing(APART_PX)
        self.bar = self._built_bar()
        self.rest()
        column.addWidget(self.bar)

    def _key_line(self, colour: str, words: str) -> QLabel:
        """One line of the key: a filled circle, then what it means."""
        line = QLabel(KEY_LINE.format(colour=colour, mark=MARK, words=words), self)
        line.setTextFormat(Qt.TextFormat.RichText)
        line.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        # Wrapped rather than clipped: a key that runs off the edge of a
        # narrowed dialog is a key nobody can read, which is the fault it
        # exists to fix.
        line.setWordWrap(True)
        return line

    def _built_bar(self) -> QProgressBar:
        """The strip that says whether the catalogue is being asked anything.

        Busy rather than counted, because one lookup has no measurable
        progress: it is a request that either comes back or is waited out.
        What a reader needs is that something is happening rather than how far
        through it is.
        """
        bar = QProgressBar(self)
        bar.setFixedHeight(ASKING_BAR_PX)
        bar.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        bar.setTextVisible(True)
        return bar

    def rest(self) -> None:
        """Back to the instruction, with nothing being asked."""
        self.bar.setRange(0, PERCENT)
        self.bar.setValue(0)
        self.bar.setFormat(NOT_ASKING)

    def say_asking(self, names: tuple[str, ...]) -> None:
        """Put whoever is being looked up on the strip, else the instruction.

        A busy range while anything is in flight, since Qt animates that: a
        bar that merely said words would look as stuck as the dialog did.
        """
        if not names:
            self.rest()
            return
        self.bar.setRange(0, 0)
        self.bar.setFormat(asking_about(names))
