"""The row at the foot of both genre choosers: cancel, then clear and filter.

Ruled by Oliver on 2026-09-13 for the chooser a discovery answer opens, then
carried to the library's own filter, which offers the same three controls; two
choosers asking one question should not dress it two ways.

**Cancel on the left, Clear beside the press that filters.** Oliver's ruling
of 2026-10-12, matching the Discover dialog: the way out stands alone on the
left, the controls that set the ticks sit together on the right. A chooser may
add one control of its own between Clear and the press that filters; both
choosers add Taste profiles there.

**Filtering wears the filter picture**, the one the tray's own filter button
wears, so the press that narrows looks like the button that opened the chooser.
**Cancelling wears that picture struck through with the negative mark**, beside
it: the one file laid over the other at run time, as every switch and the
discovery sweep do, never a second drawing. **Clearing wears the close
picture.**
"""

from __future__ import annotations

import itertools
from collections.abc import Callable, Iterable
from dataclasses import dataclass

from PySide6.QtCore import QSize
from PySide6.QtWidgets import QAbstractButton, QHBoxLayout, QPushButton, QWidget

from stellody.shared import resources
from stellody.ui.dialogs import CLOSE_ICON, CONTROL_ICON_PX, wearing
from stellody.ui.icons import struck_through

CLEAR_LABEL = "Clear"
CANCEL_LABEL = "Cancel"


@dataclass(frozen=True, slots=True)
class FilterControls:
    """What the row put on screen, laid out left to right."""

    row: QHBoxLayout
    clear: QPushButton
    cancel: QPushButton
    apply: QPushButton


def filter_controls(
    dialog: QWidget,
    apply_label: str,
    clear: Callable[[], None],
    extra: QWidget | None = None,
) -> FilterControls:
    """Cancel away to the left; clear, any extra, then the press that filters.

    The keyboard ring is stated in drawn order, since the extra control is
    made by its owner before this row exists and would otherwise come first.
    """
    row = QHBoxLayout()
    cancel_button = QPushButton(CANCEL_LABEL, dialog)
    cancel_button.setIcon(
        struck_through(
            resources.filter_icon_path(),
            resources.negative_icon_path(),
            CONTROL_ICON_PX,
        )
    )
    cancel_button.setIconSize(QSize(CONTROL_ICON_PX, CONTROL_ICON_PX))
    cancel_button.clicked.connect(dialog.reject)
    row.addWidget(cancel_button)
    row.addStretch()
    clear_button = wearing(
        QPushButton(CLEAR_LABEL, dialog), resources.find_asset(CLOSE_ICON)
    )
    clear_button.clicked.connect(clear)
    row.addWidget(clear_button)
    if extra is not None:
        row.addWidget(extra)
    apply_button = wearing(
        QPushButton(apply_label, dialog), resources.filter_icon_path()
    )
    apply_button.setDefault(True)
    apply_button.clicked.connect(dialog.accept)
    row.addWidget(apply_button)
    stops = (cancel_button, clear_button, extra, apply_button)
    drawn = [stop for stop in stops if stop is not None]
    for earlier, later in itertools.pairwise(drawn):
        QWidget.setTabOrder(earlier, later)
    return FilterControls(row, clear_button, cancel_button, apply_button)


def _never() -> bool:
    """Nothing typed is ever refused where nothing can be typed."""
    return False


def offer_apply(
    apply: QPushButton,
    boxes: Iterable[QAbstractButton],
    asking: Callable[[], bool],
    filtering_already: bool,
    refused: Callable[[], bool] = _never,
) -> Callable[[], None]:
    """Enable the press that filters only where it would change something.

    Reported by Oliver on 2026-09-13: a chooser opened with nothing ticked
    offered Filter as though there were something to filter by. With nothing
    ticked the press can only mean taking a filter off, which changes something
    where a filter was on and nothing where none was. So it waits for a tick,
    unless the chooser opened on a filter: emptying one is how a filter is
    taken off, Cancel being the press that keeps it.

    Read off the boxes at every toggle rather than counted, so Clear, a sweep
    or a box unticked by hand all move it alike.

    Years that cannot be used take the press away whatever else is ticked,
    as they take Find away in Discover (FR-D59, FR-D99). The refresh is
    handed back so a dialog can call it as the years are typed.
    """

    def refresh(*_toggled: object) -> None:
        apply.setEnabled(not refused() and (asking() or filtering_already))

    for box in boxes:
        box.toggled.connect(refresh)
    refresh()
    return refresh
