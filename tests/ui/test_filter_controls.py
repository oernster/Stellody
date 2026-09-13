"""The foot of both genre choosers wears artwork. Ruled by Oliver on 2026-09-13.

Each picture is compared with the one it should be, drawn the way the
application draws it, rather than merely checked for being there: a cancel
wearing the plain filter picture would pass a presence check while saying the
opposite of what a press does.
"""

from __future__ import annotations

from PySide6.QtCore import QSize
from PySide6.QtWidgets import QHBoxLayout

from stellody.shared import resources
from stellody.ui.dialogs import CLOSE_ICON, CONTROL_ICON_PX
from stellody.ui.filter_dialog import FilterDialog
from stellody.ui.icons import plain_icon, struck_through
from stellody.ui.results_filter import ResultsFilterDialog

SIZE = QSize(CONTROL_ICON_PX, CONTROL_ICON_PX)


def _drawn(icon):
    return icon.pixmap(SIZE).toImage()


def _choosers():
    """Each chooser with the control that filters."""
    library = FilterDialog()
    answer = ResultsFilterDialog(("House",))
    return ((library, library.show_button), (answer, answer.filter_button))


def test_filtering_wears_the_filter_picture(application) -> None:
    expected = _drawn(plain_icon(resources.filter_icon_path()))
    for _dialog, apply in _choosers():
        assert _drawn(apply.icon()) == expected


def test_cancelling_wears_the_filter_picture_struck_through(application) -> None:
    expected = _drawn(
        struck_through(
            resources.filter_icon_path(),
            resources.negative_icon_path(),
            CONTROL_ICON_PX,
        )
    )
    for dialog, apply in _choosers():
        assert _drawn(dialog.cancel_button.icon()) == expected
        assert _drawn(dialog.cancel_button.icon()) != _drawn(apply.icon())


def test_clearing_wears_the_close_picture(application) -> None:
    expected = _drawn(plain_icon(resources.find_asset(CLOSE_ICON)))
    for dialog, _apply in _choosers():
        assert _drawn(dialog.clear_button.icon()) == expected


def test_cancel_stands_beside_the_filter(application) -> None:
    for dialog, apply in _choosers():
        row = next(
            layout
            for layout in dialog.findChildren(QHBoxLayout)
            if layout.indexOf(apply) >= 0
        )
        assert row.indexOf(dialog.cancel_button) + 1 == row.indexOf(apply)
