"""The lifted list of taste profiles: a delete button, then the name. FR-D88.

Oliver's ruling of 2026-10-12: each profile carries its own delete button on
the left, so every one sits in the same column, wearing the delete picture the
shops dialog's rows wear.

**A frame rather than a menu.** A menu row holding two buttons was measured on
2026-10-12: the arrows lit the row while focus never entered either button, so
neither could be reached from the keyboard at all. A frame of real buttons is
walked explicitly instead: Up and Down move a row in the same column, Left and
Right cross between delete and name, Tab walks every button in reading order;
all of them wrap. Escape puts it down, as it does any popup.

A second press on the Taste profiles button puts it down rather than lifting it
again (`dismissal.py`), as the volume slider's popup does.

**A long list scrolls rather than leaving the screen.** Measured on 2026-10-12:
sixty profiles made a list 3436 pixels tall, which ran off an 800 pixel screen
below the button. The rows sit in a scroll area capped at the room the list
opens into, so a scroll bar shows only when they do not fit; the area takes no
focus (FR-D95), so the rows stay the only stops. A button scrolls itself into
view as it takes focus, which covers the arrows, Tab and the opening focus in
one place.
"""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QEvent, QPoint, Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QPushButton, QVBoxLayout, QWidget

from stellody.domain.taste import TasteProfile
from stellody.ui.dismissal import Dismissal
from stellody.ui.lift_menu import AMPERSAND, LITERAL_AMPERSAND
from stellody.ui.lifting import lifted_top, room
from stellody.ui.scrolling_column import scrolling_column
from stellody.ui.shop_rows import DELETE_ICON, picture_button

DELETE_TOOLTIP = "Delete the taste profile “{name}”"
# Which button of a row the arrows are on: delete in the first column (0), the
# name in the second. Crossing a row flips between the two.
NAME_COLUMN = 1
ROW_KEYS = {Qt.Key.Key_Up: -1, Qt.Key.Key_Down: 1}
COLUMN_KEYS = (Qt.Key.Key_Left, Qt.Key.Key_Right)


def _line(name: str) -> str:
    """A profile's name as a button shows it, ampersands kept."""
    return name.replace(AMPERSAND, LITERAL_AMPERSAND)


class TasteList(QFrame):
    """Every saved profile as a row: delete it; else choose it."""

    def __init__(
        self,
        parent: QWidget,
        choose: Callable[[TasteProfile], None],
        delete: Callable[[str], None],
    ) -> None:
        super().__init__(parent, Qt.WindowType.Popup)
        self.setObjectName("TasteList")
        self._choose = choose
        self._delete = delete
        self._dismissal = Dismissal()
        self._outer = QVBoxLayout(self)
        self.area, self._column = scrolling_column(self)
        self.area.setFrameShape(QFrame.Shape.NoFrame)
        self.area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._outer.addWidget(self.area)
        self.rows: list[tuple[QPushButton, QPushButton]] = []

    def fill(self, profiles: tuple[TasteProfile, ...]) -> None:
        """One row per profile, in the order given; the old rows let go of."""
        for delete, name in self.rows:
            delete.parentWidget().deleteLater()
        self.rows = []
        for profile in profiles:
            holder = QWidget(self.area.widget())
            line = QHBoxLayout(holder)
            line.setContentsMargins(0, 0, 0, 0)
            delete = picture_button(
                DELETE_ICON, DELETE_TOOLTIP.format(name=profile.name), holder
            )
            delete.clicked.connect(
                lambda _checked=False, gone=profile.name: self._then(
                    lambda: self._delete(gone)
                )
            )
            name = QPushButton(_line(profile.name), holder)
            name.setAutoDefault(False)
            name.clicked.connect(
                lambda _checked=False, chosen=profile: self._then(
                    lambda: self._choose(chosen)
                )
            )
            delete.installEventFilter(self)
            name.installEventFilter(self)
            line.addWidget(delete)
            line.addWidget(name, 1)
            self._column.addWidget(holder)
            self.rows.append((delete, name))
        self.adjustSize()

    def _then(self, act: Callable[[], None]) -> None:
        """Put the list down, then act: a question asked over it would close it."""
        self.hide()
        act()

    def open_above(self, button: QWidget) -> None:
        """Lift over the button; put down when it is already up."""
        if self.isVisible():
            self.hide()
            return
        if self._dismissal.dismissed_by(button) or not self.rows:
            return
        self._dismissal.forget()
        self._fit(room(button))
        left = button.mapToGlobal(QPoint(0, 0)).x()
        self.move(left, lifted_top(self.sizeHint().height(), button))
        self.show()
        self.rows[0][NAME_COLUMN].setFocus(Qt.FocusReason.PopupFocusReason)

    def _fit(self, tallest: int) -> None:
        """Every row where they fit in this height; else as many as do, scrolling."""
        rows = self.area.widget().sizeHint()
        chrome = sum(
            edge.top() + edge.bottom()
            for edge in (self._outer.contentsMargins(), self.contentsMargins())
        )
        height = min(rows.height(), tallest - chrome)
        scrolls = height < rows.height()
        bar = self.area.verticalScrollBar().sizeHint().width() if scrolls else 0
        self.area.setFixedSize(rows.width() + bar, height)
        self.adjustSize()

    def eventFilter(self, watched, event) -> bool:
        """Up and Down keep the column; Left and Right cross the row; both wrap.

        Taken from the buttons before they see it: a push button answers the
        arrows itself, moving to whichever button lies nearest that way, which
        measured on 2026-10-12 took Down from a name to the next row's delete.
        A button taking focus, however it got there, is scrolled into view.
        """
        if event.type() == QEvent.Type.FocusIn:
            self.area.ensureWidgetVisible(watched)
        if event.type() != QEvent.Type.KeyPress:
            return super().eventFilter(watched, event)
        key = event.key()
        place = self._place(watched)
        if place is None or (key not in ROW_KEYS and key not in COLUMN_KEYS):
            return super().eventFilter(watched, event)
        row, column = place
        if key in ROW_KEYS:
            row = (row + ROW_KEYS[key]) % len(self.rows)
        else:
            column = NAME_COLUMN - column
        self.rows[row][column].setFocus(Qt.FocusReason.TabFocusReason)
        return True

    def _place(self, button: object) -> tuple[int, int] | None:
        """The row and column of this button; None where it is in no row."""
        for row, buttons in enumerate(self.rows):
            if button in buttons:
                return row, buttons.index(button)
        return None

    def mousePressEvent(self, event) -> None:
        """Close on a press outside, remembering where that press landed."""
        self._dismissal.note(self, event)
        super().mousePressEvent(event)
