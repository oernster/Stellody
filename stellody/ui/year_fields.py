"""The two year fields in the discovery dialog: released from, to. FR-D58.

Two plain text fields rather than spin boxes. A spin box holds a number it has
clamped into its range, so a year typed outside it would be quietly changed to
one that fits; FR-D59 wants that refused and said instead. Empty means no bound,
which a spin box cannot say at all.

**What the fields mean is the domain's; what is said about them is here.** The
fields hand over their text and the domain reads it, so the rule about which
years are plausible has one home and this module holds only the words.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QLineEdit, QWidget

from stellody.domain.release_years import (
    FIRST_YEAR,
    Bound,
    ReleaseYears,
    YearFault,
    YearRefusal,
    last_year,
    read_years,
)

FROM_LABEL = "Released from"
TO_LABEL = "to"
# Said in an empty field, since empty is a choice rather than something missing.
ANY_YEAR_HINT = "any year"
# A year is typed as four digits; the field takes no more than that.
YEAR_DIGITS = 4
# Wide enough for four digits or the hint in the dialog's font.
YEAR_FIELD_PX = 80
FIELD_NAMES = {Bound.EARLIEST: "The from year", Bound.LATEST: "The to year"}
FAULTS = {
    YearFault.NOT_A_YEAR: "{field} is not a year: type four digits, such as 1985.",
    YearFault.TOO_EARLY: (
        "{field} is before {first}, the earliest year that can be asked about."
    ),
    YearFault.TOO_LATE: (
        "{field} is after {last}, the latest year that can be asked about."
    ),
    YearFault.REVERSED: "The from year is later than the to year.",
}


def refusal_words(refusal: YearRefusal, this_year: int) -> str:
    """Which field is wrong and why, in the words the dialog says it in."""
    return FAULTS[refusal.fault].format(
        field=FIELD_NAMES[refusal.bound], first=FIRST_YEAR, last=last_year(this_year)
    )


class YearFields(QWidget):
    """Released from, to: two optional years, read together.

    The row itself takes no focus and wears no ring; the two fields do, in
    the order they are read.
    """

    changed = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.addWidget(QLabel(FROM_LABEL, self))
        self.earliest = self._field()
        row.addWidget(self.earliest)
        row.addWidget(QLabel(TO_LABEL, self))
        self.latest = self._field()
        row.addWidget(self.latest)
        row.addStretch()

    def _field(self) -> QLineEdit:
        """One empty year field, saying so."""
        field = QLineEdit(self)
        field.setPlaceholderText(ANY_YEAR_HINT)
        field.setMaxLength(YEAR_DIGITS)
        field.setFixedWidth(YEAR_FIELD_PX)
        field.textChanged.connect(self.changed)
        return field

    def reading(self, this_year: int) -> ReleaseYears | YearRefusal:
        """The years the two fields ask for; else why they cannot be used."""
        return read_years(self.earliest.text(), self.latest.text(), this_year)
