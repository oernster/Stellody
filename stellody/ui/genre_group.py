"""One main genre with its styles folded away beneath it.

The catalogue has 57 boxes, which at full height asked for a dialog wider than
a laptop or taller than one. Ruled by Oliver on 2026-10-01: each category folds
behind an arrow, so the grid shows its 21 mains and opens only the ones being
looked at.

**The arrow is a control, so it is a stop on the keyboard ring.** It is made
before its main's box, so Tab reaches it first and Enter or Space opens the
category; the styles that appear are then the next stops. Folded styles are
hidden, which takes them off the ring by the same rule that takes any hidden
control off it.

**A folded category still says what is ticked inside it.** A count beside the
main's name, so a style ticked and then folded away is never a choice nobody
can see.
"""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from stellody.ui.ringed_check import RingedCheckBox

# What the arrow shows in each state: pointing at the main while folded,
# pointing down at the styles while they are showing.
FOLDED_GLYPH = "▸"
OPEN_GLYPH = "▾"
# Said by the arrow to a screen reader and on hover, since a glyph says nothing.
FOLD_TIP = "Show or hide the styles of {main}"
# Said beside a folded main holding ticked styles.
TICKED_COUNT = "({count})"
# How wide the arrow is drawn. Held fixed, so every main's box starts at the
# same place whether or not it has styles to fold.
FOLD_PX = 24
# How far a style sits in from the main it belongs to. Enough to read as
# beneath it rather than beside it, without pushing the longest name out of
# the dialog.
INDENT_PX = 18
# Narrows the house button to the arrow it carries. Scoped to its own name, so
# nothing the arrow holds, its tooltip included, inherits it; the ring rules of
# the application sheet still apply, since this sets padding alone.
ARROW_NAME = "GenreFold"
ARROW_SHEET = f"QPushButton#{ARROW_NAME} {{ padding: 0px; }}"

MakeBox = Callable[[str, QWidget], RingedCheckBox]


class GenreGroup(QWidget):
    """A main's box, its arrow and its styles, folded or open."""

    folded = Signal()

    def __init__(
        self,
        main: str,
        styles: tuple[str, ...],
        make_box: MakeBox,
        opened: bool,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.main = main
        # Chrome rather than a control: the arrow and the boxes are the stops.
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        # Made first, so it comes before the main's box on the ring.
        self.arrow = QPushButton(FOLDED_GLYPH, self)
        self.arrow.setObjectName(ARROW_NAME)
        self.arrow.setStyleSheet(ARROW_SHEET)
        self.arrow.setFixedWidth(FOLD_PX)
        self.arrow.setCheckable(True)
        self.arrow.setToolTip(FOLD_TIP.format(main=main))
        self.arrow.setAccessibleName(FOLD_TIP.format(main=main))
        # A main with no styles keeps the arrow's room, so the boxes line up.
        kept = self.arrow.sizePolicy()
        kept.setRetainSizeWhenHidden(True)
        self.arrow.setSizePolicy(kept)
        header.addWidget(self.arrow)
        self.box = make_box(main, self)
        header.addWidget(self.box)
        self.count = QLabel("", self)
        header.addWidget(self.count)
        header.addStretch()
        outer.addLayout(header)

        self.styles = QWidget(self)
        self.styles.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.styles.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum
        )
        under = QVBoxLayout(self.styles)
        under.setContentsMargins(FOLD_PX + INDENT_PX, 0, 0, 0)
        under.setSpacing(0)
        self.style_boxes = tuple(make_box(style, self.styles) for style in styles)
        for box in self.style_boxes:
            under.addWidget(box)
            box.toggled.connect(self._say_count)
        outer.addWidget(self.styles)

        self.arrow.setChecked(opened)
        self.arrow.toggled.connect(self._fold)
        self._show(opened)
        self.offer_arrow()

    def is_open(self) -> bool:
        """Whether its styles are showing."""
        return self.arrow.isChecked()

    def set_open(self, opened: bool) -> None:
        """Open or fold it, as a press of the arrow would."""
        self.arrow.setChecked(opened)

    def offer_arrow(self) -> None:
        """Offer the arrow only where there is a style to show.

        Asked again whenever a host hides boxes it does not offer, since a
        category whose every style is hidden has nothing to open; one with no
        box on offer at all is hidden whole rather than left as a blank line.
        """
        any_style = any(not box.isHidden() for box in self.style_boxes)
        self.arrow.setHidden(not any_style)
        self.setHidden(not any_style and self.box.isHidden())

    def _fold(self, opened: bool) -> None:
        self._show(opened)
        self.folded.emit()

    def _show(self, opened: bool) -> None:
        self.arrow.setText(OPEN_GLYPH if opened else FOLDED_GLYPH)
        self.styles.setVisible(opened)
        self._say_count()

    def _say_count(self) -> None:
        """The ticked styles out of sight, counted; nothing while they show."""
        ticked = sum(box.isChecked() for box in self.style_boxes)
        hidden = not self.is_open() and ticked
        self.count.setText(TICKED_COUNT.format(count=ticked) if hidden else "")
