"""The arrow at the left of the Title heading opens or shuts the whole library.

Driven by pressing the heading where the arrow is drawn rather than by calling
the toggle, since where the press lands is half of what is being asserted: a
press on the rest of the heading has to stay the heading's own.
"""

from __future__ import annotations

from playback_support import player, window
from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QMouseEvent

from stellody.ui.expanding import ExpandToggle
from stellody.ui.main_window import MainWindow
from stellody.ui.row_text import Column

__all__ = ["player", "window"]


def press(header, where: QPoint) -> None:
    """One left press on the heading, at a point in its own coordinates."""
    header.mousePressEvent(
        QMouseEvent(
            QMouseEvent.Type.MouseButtonPress,
            where,
            header.mapToGlobal(where),
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        )
    )


def toggle_of(window: MainWindow) -> ExpandToggle:
    """The one keeping the arrow and the rows in step."""
    found = window._tree.findChildren(ExpandToggle)
    assert len(found) == 1
    return found[0]


def album(window: MainWindow):
    """The first album's row."""
    return window._model.index(0, Column.TITLE)


def test_a_press_on_the_arrow_opens_every_album(window: MainWindow) -> None:
    """The library opens collapsed, so the first press is the opening one."""
    header = window._tree.header()
    assert not window._tree.isExpanded(album(window))

    press(header, header.indicator().center())

    assert window._tree.isExpanded(album(window))


def test_a_second_press_shuts_them_again(window: MainWindow) -> None:
    """The gesture that opened them asked to undo itself."""
    header = window._tree.header()
    press(header, header.indicator().center())
    press(header, header.indicator().center())

    assert not window._tree.isExpanded(album(window))


def test_a_press_elsewhere_on_the_heading_opens_nothing(window: MainWindow) -> None:
    """Only the arrow is the toggle; the rest of the heading is the heading."""
    header = window._tree.header()
    beyond = QPoint(header.indicator().right() + 40, header.height() // 2)

    press(header, beyond)

    assert not window._tree.isExpanded(album(window))


def test_the_arrow_follows_albums_opened_by_hand(window: MainWindow) -> None:
    """Read off the rows rather than remembered, so it cannot drift.

    One album opened by hand is every album in this library, which is what
    makes the arrow turn down without the toggle having been touched.
    """
    toggle = toggle_of(window)
    assert not toggle.all_open()

    window._tree.expand(album(window))

    assert toggle.all_open()

    window._tree.collapse(album(window))

    assert not toggle.all_open()


def test_an_empty_library_is_not_reported_as_wide_open(window: MainWindow) -> None:
    """Nothing to open is not everything open, whatever `all` answers."""
    toggle = toggle_of(window)
    window._model.set_albums(())

    assert not toggle.all_open()


def strip_of(window: MainWindow) -> list:
    """The pixels where the arrow is drawn, read off the painted heading."""
    header = window._tree.header()
    shot = header.grab().toImage()
    where = header.indicator()
    return [
        shot.pixelColor(x, y).name()
        for x in range(where.left(), where.right() + 1)
        for y in range(where.top(), where.bottom() + 1)
    ]


def test_the_arrow_itself_changes_when_everything_opens(window: MainWindow) -> None:
    """The state is read off the paint, not off the flag behind it.

    A toggle whose arrow never turned would be one nobody could read; an
    assertion about the flag alone would pass the whole time it did not.
    """
    window.show()
    shut = strip_of(window)

    window.expanding.open_all()
    open_now = strip_of(window)

    assert window.expanding.all_open()
    assert open_now != shut
    assert set(shut) != {shut[0]}
