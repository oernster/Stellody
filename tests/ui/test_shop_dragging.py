"""A shop row carried with the pointer while it is dragged. FR-S27, Amendment 2.

Driven through the handle's own mouse events rather than by calling the drag,
so what is proved is the path a real press, movement and release take.
"""

from __future__ import annotations

from PySide6.QtCore import QEvent, QPoint, QPointF, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from test_shop_editing import BLEEP, JUNO, QOBUZ, dialog_over

from stellody.infrastructure.shop_file import DEFAULT_SHOPS
from stellody.ui.shop_dragging import LAND_MS, ROOM_MS
from stellody.ui.shop_rows import Handle

LEFT = Qt.MouseButton.LeftButton
NO_BUTTON = Qt.MouseButton.NoButton
# A small movement, well inside the room a row has to travel.
NUDGE_PX = 5
# Both runs laid end to end, which outlasts either of them alone.
SETTLE_MS = ROOM_MS + LAND_MS


def _send(handle: Handle, kind: QEvent.Type, where: QPoint, button, buttons) -> None:
    """One mouse event at the screen point `where`, delivered to the handle."""
    local = QPointF(handle.mapFromGlobal(where))
    event = QMouseEvent(
        kind, local, QPointF(where), button, buttons, Qt.KeyboardModifier.NoModifier
    )
    QApplication.sendEvent(handle, event)


def _press(handle: Handle, where: QPoint) -> None:
    _send(handle, QEvent.Type.MouseButtonPress, where, LEFT, LEFT)


def _move(handle: Handle, where: QPoint) -> None:
    _send(handle, QEvent.Type.MouseMove, where, NO_BUTTON, LEFT)


def _release(handle: Handle, where: QPoint) -> None:
    _send(handle, QEvent.Type.MouseButtonRelease, where, LEFT, NO_BUTTON)


def _handle(dialog, index: int) -> Handle:
    return dialog.controls[index].holder.findChild(Handle)


def _middle(widget) -> QPoint:
    return widget.mapToGlobal(widget.rect().center())


def _tops(dialog) -> list[int]:
    return [made.holder.y() for made in dialog.controls]


def _to_the_top(dialog) -> tuple[Handle, QPoint]:
    """Take the third row's grip and carry it level with the first row."""
    handle = _handle(dialog, 2)
    start = _middle(handle)
    tops = _tops(dialog)
    _press(handle, start)
    over_first = start + QPoint(0, tops[0] - tops[2])
    _move(handle, over_first)
    return handle, over_first


def _shown(dialog) -> list[str]:
    return list(dialog.shop_buttons)


def test_the_held_row_follows_the_pointer(application) -> None:
    """It moves as the pointer moves, before anything is let go."""
    dialog, store, *_rest = dialog_over(QOBUZ, BLEEP, JUNO)
    application.processEvents()
    handle, row = _handle(dialog, 2), dialog.controls[2].holder
    start, before = _middle(handle), row.y()
    _press(handle, start)
    _move(handle, start - QPoint(0, NUDGE_PX))
    assert row.y() == before - NUDGE_PX
    assert store.held.rows == (QOBUZ, BLEEP, JUNO)
    _release(handle, start)


def test_the_other_rows_make_room_before_it_is_let_go(application) -> None:
    """Carried over the first row, the first two glide down one place each."""
    dialog, store, *_rest = dialog_over(QOBUZ, BLEEP, JUNO)
    application.processEvents()
    tops = _tops(dialog)
    handle, over_first = _to_the_top(dialog)
    QTest.qWait(SETTLE_MS)
    assert dialog.drag.target == 0
    assert [dialog.controls[0].holder.y(), dialog.controls[1].holder.y()] == tops[1:]
    assert store.held.rows == (QOBUZ, BLEEP, JUNO)
    _release(handle, over_first)


def test_dragging_the_handle_moves_the_shop(application) -> None:
    """FR-S27: written the moment it is let go, then drawn where it landed."""
    dialog, store, *_rest = dialog_over(QOBUZ, BLEEP, JUNO)
    application.processEvents()
    tops = _tops(dialog)
    handle, over_first = _to_the_top(dialog)
    _release(handle, over_first)
    assert store.held.rows == (JUNO, QOBUZ, BLEEP)
    QTest.qWait(SETTLE_MS)
    assert _shown(dialog) == ["Juno", "Qobuz", "Bleep"]
    assert _tops(dialog) == tops


def test_a_move_the_file_refuses_glides_back(application) -> None:
    """FR-S29: nothing is shown as moved when nothing was written."""
    dialog, store, *_rest = dialog_over(QOBUZ, BLEEP, JUNO, refuse=True)
    application.processEvents()
    handle, over_first = _to_the_top(dialog)
    _release(handle, over_first)
    assert "could not be saved" in dialog.said.text()
    QTest.qWait(SETTLE_MS)
    assert store.held.rows == (QOBUZ, BLEEP, JUNO)
    assert _shown(dialog) == ["Qobuz", "Bleep", "Juno"]
    # The message takes room of its own, so the rows sit higher than they
    # started; what matters is that they stand in their old order again.
    tops = _tops(dialog)
    assert tops == sorted(tops)
    assert dialog.controls[2].holder.y() == max(tops)


def test_letting_go_where_it_was_taken_writes_nothing(application) -> None:
    """A file that refuses every write says nothing, so none was tried."""
    dialog, _store, *_rest = dialog_over(QOBUZ, BLEEP, refuse=True)
    application.processEvents()
    tops = _tops(dialog)
    handle = _handle(dialog, 1)
    start = _middle(handle)
    _press(handle, start)
    _release(handle, start)
    QTest.qWait(SETTLE_MS)
    assert dialog.said.text() == ""
    assert _tops(dialog) == tops
    assert not dialog.drag.busy


def test_every_shop_can_be_dragged_to_the_bottom(application) -> None:
    """Reported by Oliver on 2026-09-13: the last place could not be reached.

    Over the eight shipped shops, as a real list holds them. Measured before
    the fix: all seven rows stopped one place short, because a row held at
    the lowest point has its middle exactly level with the last row's, which a
    three row list with one taller row did not show.
    """
    last = len(DEFAULT_SHOPS) - 1
    for index in range(last):
        dialog, store, *_rest = dialog_over(*DEFAULT_SHOPS)
        application.processEvents()
        handle = _handle(dialog, index)
        start = _middle(handle)
        far_below = start + QPoint(0, _tops(dialog)[last] * len(DEFAULT_SHOPS))
        _press(handle, start)
        _move(handle, far_below)
        assert dialog.drag.target == last, DEFAULT_SHOPS[index].name
        _release(handle, far_below)
        assert store.held.rows[-1] == DEFAULT_SHOPS[index]
        QTest.qWait(SETTLE_MS)
        dialog.close()


def test_the_keyboard_waits_while_a_row_is_held(application) -> None:
    """Ctrl+Up during a drag would redraw the rows out from under it."""
    dialog, store, *_rest = dialog_over(QOBUZ, BLEEP, JUNO)
    application.processEvents()
    handle, over_first = _to_the_top(dialog)
    dialog.controls[1].button.setFocus()
    dialog.move_focused(-1)
    assert store.held.rows == (QOBUZ, BLEEP, JUNO)
    _release(handle, over_first)
