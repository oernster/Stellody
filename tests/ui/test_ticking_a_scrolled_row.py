"""A click on a box further down the answer ticks that box, where it is.

Reported by Oliver on 2026-10-04: with the list scrolled down, a click on an
album's box often threw the list back up a long way and ticked nothing. The
first click into a list is the one that does it, since it is also the click
that gives the list focus.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import (
    QApplication,
    QLineEdit,
    QStyle,
    QStyleOptionViewItem,
    QVBoxLayout,
    QWidget,
)

from stellody.domain.discovery import Gaps, ReleaseGroup
from stellody.ui.palette import Mode, palette_for
from stellody.ui.results_ticks import TICKED, is_tickable
from stellody.ui.results_tree import filled_tree

SOURCE_COUNT = 30
ALBUMS_EACH = 4
WINDOW_HEIGHT = 300


def long_answer() -> tuple[Gaps, ...]:
    """More rows than any window shows, so the list has to scroll."""
    return tuple(
        Gaps(
            artist=f"Artist {source}",
            albums=tuple(
                ReleaseGroup(title=f"Album {source}.{album}")
                for album in range(ALBUMS_EACH)
            ),
        )
        for source in range(SOURCE_COUNT)
    )


def box_centre(tree, item):
    """Where on the viewport the row's tick box is drawn."""
    index = tree.indexFromItem(item)
    option = QStyleOptionViewItem()
    option.rect = tree.visualRect(index)
    tree.itemDelegate().initStyleOption(option, index)
    option.widget = tree
    box = tree.style().subElementRect(
        QStyle.SubElement.SE_ItemViewItemCheckIndicator, option, tree
    )
    return box.center()


def shown_beside_a_field(application: QApplication):
    """A long list on screen, with focus in a field beside it."""
    window = QWidget()
    layout = QVBoxLayout(window)
    elsewhere = QLineEdit(window)
    tree = filled_tree(long_answer(), palette_for(Mode.DARK), {}, window)
    layout.addWidget(elsewhere)
    layout.addWidget(tree)
    window.resize(window.width(), WINDOW_HEIGHT)
    window.show()
    window.activateWindow()
    QTest.qWaitForWindowExposed(window)
    elsewhere.setFocus()
    application.processEvents()
    assert not tree.hasFocus(), "focus starts away from the list"
    assert tree.currentItem() is None, "nothing is current to begin with"
    return window, tree


def test_tabbing_into_the_list_still_arrives_on_the_first_row(
    application: QApplication,
) -> None:
    """The keyboard keeps its landing place; only a click gives it up."""
    window, tree = shown_beside_a_field(application)
    tree.setFocus(Qt.FocusReason.TabFocusReason)
    application.processEvents()
    assert tree.currentItem() is tree.topLevelItem(0)
    window.close()


def test_a_first_click_far_down_ticks_that_box_without_scrolling(
    application: QApplication,
) -> None:
    window, tree = shown_beside_a_field(application)

    bar = tree.verticalScrollBar()
    bar.setValue(bar.maximum())
    application.processEvents()
    scrolled = bar.value()
    assert scrolled > 0, "the list really did scroll"

    last_source = tree.topLevelItem(SOURCE_COUNT - 1)
    target = last_source.child(ALBUMS_EACH - 1)
    assert is_tickable(target)
    QTest.mouseClick(
        tree.viewport(), Qt.MouseButton.LeftButton, pos=box_centre(tree, target)
    )
    application.processEvents()

    assert bar.value() == scrolled, "the click threw the list somewhere else"
    assert target.checkState(0) is TICKED, "the box clicked was not ticked"
    window.close()
