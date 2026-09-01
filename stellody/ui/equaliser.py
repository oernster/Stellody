"""The equalizer: one slider to a band, plus the switch that engages it.

Ten sliders across, read left to right as low to high, each labelled with the
frequency it sits on and reading its own gain above. The switch is separate
from the sliders so that turning the equalizer off leaves the curve where it
was: somebody comparing on against off is asking one question; losing their
settings to it would answer a different one.

The dialog owns no state. Every move hands a whole new `Equalisation` outward
and the window decides what to do with it, which is what lets the sound change
as a slider is dragged rather than when the dialog is closed.
"""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from stellody.domain.equalising import (
    BAND_FREQUENCIES,
    FLAT_DB,
    MAXIMUM_GAIN_DB,
    MINIMUM_GAIN_DB,
    Equalisation,
)
from stellody.ui.dialogs import NeutralDialog, close_row
from stellody.ui.ringed_check import RingedCheckBox

SLIDER_HEIGHT_PX = 160
COLUMN_SPACING_PX = 6
MARGIN_PX = 12
# Whole decibels: the step a listener can actually hear on one band, which is
# what the reading above the slider says.
GAIN_STEP_DB = 1
PAGE_STEP_DB = 3
# Above a thousand a frequency reads better in kilohertz, which is how every
# equalizer a listener has met before labels these.
KILO = 1000

SWITCH_LABEL = "Shape the sound"
SWITCH_TOOLTIP = "Apply the curve below, else play the file exactly as it is"
FLAT_LABEL = "Flat"
FLAT_TOOLTIP = "Put every band back to nought, leaving the switch as it is"
TITLE = "Equalizer"


def band_label(frequency: int) -> str:
    """One band's frequency, said the way an equalizer usually says it."""
    if frequency < KILO:
        return f"{frequency}"
    return f"{frequency // KILO}k"


def gain_label(gain_db: int) -> str:
    """One band's gain, signed so a cut and a lift are told apart at a glance."""
    return f"{gain_db:+d}"


class _Band(QWidget):
    """One vertical slider, its reading above it and its frequency below."""

    def __init__(
        self, parent: QWidget, frequency: int, on_change: Callable[[int], None]
    ) -> None:
        super().__init__(parent)
        self.reading = QLabel(gain_label(0), self)
        self.reading.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self.slider = QSlider(Qt.Orientation.Vertical, self)
        self.slider.setObjectName("EqualiserBand")
        self.slider.setRange(int(MINIMUM_GAIN_DB), int(MAXIMUM_GAIN_DB))
        self.slider.setSingleStep(GAIN_STEP_DB)
        self.slider.setPageStep(PAGE_STEP_DB)
        self.slider.setFixedHeight(SLIDER_HEIGHT_PX)
        self.slider.setToolTip(f"{frequency} hertz")
        self.slider.valueChanged.connect(self._show_gain)
        self.slider.valueChanged.connect(on_change)
        name = QLabel(band_label(frequency), self)
        name.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        column = QVBoxLayout(self)
        column.setContentsMargins(0, 0, 0, 0)
        column.addWidget(self.reading, alignment=Qt.AlignmentFlag.AlignHCenter)
        column.addWidget(self.slider, alignment=Qt.AlignmentFlag.AlignHCenter)
        column.addWidget(name, alignment=Qt.AlignmentFlag.AlignHCenter)

    def _show_gain(self, gain_db: int) -> None:
        """Keep the reading above the slider true as the handle moves."""
        self.reading.setText(gain_label(gain_db))

    def show_gain(self, gain_db: float) -> None:
        """Put the handle where a stored curve says, without reporting it."""
        blocked = self.slider.blockSignals(True)
        self.slider.setValue(int(gain_db))
        self.slider.blockSignals(blocked)
        self._show_gain(int(gain_db))


class EqualiserDialog(NeutralDialog):
    """Ten bands and a switch, reporting the whole curve on every move."""

    def __init__(
        self,
        parent: QWidget,
        equalisation: Equalisation,
        on_change: Callable[[Equalisation], None],
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(TITLE)
        self._on_change = on_change
        self._equalisation = equalisation
        self.switch = RingedCheckBox(SWITCH_LABEL, self)
        self.switch.setToolTip(SWITCH_TOOLTIP)
        self.switch.toggled.connect(self._switched)
        self.flatten = QPushButton(FLAT_LABEL, self)
        self.flatten.setToolTip(FLAT_TOOLTIP)
        self.flatten.clicked.connect(self._flatten)
        self.bands = tuple(
            _Band(self, frequency, self._moved) for frequency in BAND_FREQUENCIES
        )
        column = QVBoxLayout(self)
        column.setContentsMargins(MARGIN_PX, MARGIN_PX, MARGIN_PX, MARGIN_PX)
        column.addLayout(self._top_row())
        column.addLayout(self._band_row())
        column.addLayout(close_row(self))
        self.show_equalisation(equalisation)

    def _top_row(self) -> QHBoxLayout:
        """The switch at the left, the way back to flat at the right."""
        row = QHBoxLayout()
        row.addWidget(self.switch)
        row.addStretch()
        row.addWidget(self.flatten)
        return row

    def _band_row(self) -> QHBoxLayout:
        """The bands themselves, low at the left as every equalizer draws them."""
        row = QHBoxLayout()
        row.setSpacing(COLUMN_SPACING_PX)
        for band in self.bands:
            row.addWidget(band)
        return row

    def show_equalisation(self, equalisation: Equalisation) -> None:
        """Show a curve without reporting it back as though it were a move."""
        self._equalisation = equalisation
        blocked = self.switch.blockSignals(True)
        self.switch.setChecked(equalisation.enabled)
        self.switch.blockSignals(blocked)
        for band, gain in zip(self.bands, equalisation.gains_db):
            band.show_gain(gain)

    def _moved(self, _gain_db: int) -> None:
        """One band moved, so the whole curve is read off and handed outward."""
        gains = tuple(float(band.slider.value()) for band in self.bands)
        self._report(Equalisation(gains_db=gains, enabled=self._equalisation.enabled))

    def _switched(self, enabled: bool) -> None:
        """The switch moved, which leaves every band exactly where it was."""
        self._report(self._equalisation.switched(enabled))

    def _flatten(self) -> None:
        """Every band back to nought, the switch left alone."""
        self.show_equalisation(self._equalisation.levelled())
        self._report(self._equalisation)

    def _report(self, equalisation: Equalisation) -> None:
        """Hold the new curve and tell whoever is listening about it."""
        self._equalisation = equalisation
        self._on_change(equalisation)


__all__ = ["FLAT_DB", "EqualiserDialog", "band_label", "gain_label"]
