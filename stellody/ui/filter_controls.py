"""The row at the foot of both genre choosers: clear, then cancel and filter.

Ruled by Oliver on 2026-09-13 for the chooser a discovery answer opens, then
carried to the library's own filter, which offers the same three controls; two
choosers asking one question should not dress it two ways.

**Filtering wears the filter picture**, the one the tray's own filter button
wears, so the press that narrows looks like the button that opened the chooser.
**Cancelling wears that picture struck through with the negative mark**, beside
it: the one file laid over the other at run time, as every switch and the
discovery sweep do, never a second drawing. **Clearing wears the close
picture.**
"""

from __future__ import annotations

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
    dialog: QWidget, apply_label: str, clear: Callable[[], None]
) -> FilterControls:
    """Clear away to the left, then cancel beside the press that filters."""
    row = QHBoxLayout()
    clear_button = wearing(
        QPushButton(CLEAR_LABEL, dialog), resources.find_asset(CLOSE_ICON)
    )
    clear_button.clicked.connect(clear)
    row.addWidget(clear_button)
    row.addStretch()
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
    apply_button = wearing(
        QPushButton(apply_label, dialog), resources.filter_icon_path()
    )
    apply_button.setDefault(True)
    apply_button.clicked.connect(dialog.accept)
    row.addWidget(apply_button)
    return FilterControls(row, clear_button, cancel_button, apply_button)


def offer_apply(
    apply: QPushButton,
    boxes: Iterable[QAbstractButton],
    asking: Callable[[], bool],
    filtering_already: bool,
) -> None:
    """Enable the press that filters only where it would change something.

    Reported by Oliver on 2026-09-13: a chooser opened with nothing ticked
    offered Filter as though there were something to filter by. With nothing
    ticked the press can only mean taking a filter off, which changes something
    where a filter was on and nothing where none was. So it waits for a tick,
    unless the chooser opened on a filter: emptying one is how a filter is
    taken off, Cancel being the press that keeps it.

    Read off the boxes at every toggle rather than counted, so Clear, a sweep
    or a box unticked by hand all move it alike.
    """

    def refresh(*_toggled: object) -> None:
        apply.setEnabled(asking() or filtering_already)

    for box in boxes:
        box.toggled.connect(refresh)
    refresh()
