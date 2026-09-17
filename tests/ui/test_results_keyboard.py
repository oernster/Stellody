"""The results screen from the keyboard: where it starts, the ring, the rows.

Reported by Oliver on 2026-09-17 against the installed build: the ticks never
took the focus and opening or shutting an artist from the keyboard half worked,
in a way that did not work right. Measured the same day over the real window:
the dialog opened on a button beneath the lists and reached the lists last;
Left and Right stepped the ring out of a list rather than opening or shutting
the artist under the cursor, except on a similar artist, where Right opened it;
Enter and Space did nothing on an artist; Enter did not tick an album.

Ruled the same day, following the library list: the dialog opens on the first
list with its first row current; the ring is the lists left to right then the
controls beneath them in the order they are drawn; Up and Down walk the rows;
Right opens an artist and Left shuts it; Enter and Space tick an album and open
or shut an artist; the current row wears the ring while its list has the focus.

Built over the real window, since the rule that makes Left and Right step the
ring is installed by the window and a dialog built without one never meets it.
"""

from __future__ import annotations

import pytest
from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QColor
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QStyle
from results_support import gaps_with
from ring_support import build_ring_window

from stellody.ui.results_dialog import ResultsDialog
from stellody.ui.results_ticks import (
    TICKED,
    UNTICKED,
    BoxedTicks,
    every_row,
    is_tickable,
)
from stellody.ui.theme import Mode, palette_for

# Room for three lists side by side: what a 13 inch display gives the dialog.
THREE_LISTS = QSize(1279, 752)
CHOOSING_KEYS = (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Space)


@pytest.fixture
def window(application: QApplication):
    yield from build_ring_window(application)


@pytest.fixture
def dialog(application: QApplication, window, monkeypatch: pytest.MonkeyPatch):
    """A results screen of three lists over the real window, open and active."""
    monkeypatch.setattr(ResultsDialog, "_opening_size", lambda _self: THREE_LISTS)
    gaps = tuple(gaps_with(albums=2, artists=1, artist=f"Source {n}") for n in range(6))
    made = ResultsDialog(gaps, mode=Mode.DARK, parent=window)
    made.show()
    made.activateWindow()
    application.processEvents()
    yield made
    made.close()
    made.deleteLater()


def pressed(application: QApplication, key: Qt.Key) -> None:
    """Press a key where the dialog's focus is, as the keyboard would."""
    QTest.keyClick(QApplication.focusWidget(), key)
    application.processEvents()


def first_album(dialog: ResultsDialog):
    source = dialog.sources[0]
    return next(
        source.child(at)
        for at in range(source.childCount())
        if is_tickable(source.child(at))
    )


def first_candidate(dialog: ResultsDialog):
    source = dialog.sources[0]
    return next(
        source.child(at)
        for at in range(source.childCount())
        if not is_tickable(source.child(at))
    )


def standing_on(application: QApplication, dialog: ResultsDialog, item) -> None:
    tree = dialog.pages.trees[0]
    tree.setFocus(Qt.FocusReason.TabFocusReason)
    tree.setCurrentItem(item)
    application.processEvents()


class TestWhereItStarts:
    def test_it_opens_on_the_first_list(self, dialog: ResultsDialog) -> None:
        assert len(dialog.pages.trees) == 3, "three lists to walk"
        assert QApplication.focusWidget() is dialog.pages.trees[0]

    def test_the_first_row_is_current_on_arrival(self, dialog: ResultsDialog) -> None:
        """A list arrived at with nothing current shows nothing at all."""
        assert dialog.pages.trees[0].currentItem() is dialog.sources[0]


def controls_as_drawn(dialog: ResultsDialog) -> list:
    """The controls beneath the answer, left to right, every one enabled.

    Enabled by hand, since a control that is off is rightly passed over and an
    order measured with half the row inert measures the wrong list.
    """
    controls = [
        dialog.filter_button,
        dialog.copy_button,
        dialog.shops_button,
        dialog.pager.previous_button,
        dialog.pager.next_button,
        dialog.close_button,
    ]
    for control in controls:
        control.setEnabled(True)
    return controls


class TestTheRing:
    def test_tab_walks_the_lists_then_the_controls_as_drawn(
        self, application: QApplication, dialog: ResultsDialog
    ) -> None:
        expected = [
            *dialog.pages.trees[1:],
            *controls_as_drawn(dialog),
            dialog.pages.trees[0],
        ]
        reached = []
        for _ in expected:
            pressed(application, Qt.Key.Key_Tab)
            reached.append(QApplication.focusWidget())
        assert reached == expected

    def test_the_order_survives_the_answer_being_dealt_again(
        self, application: QApplication, dialog: ResultsDialog
    ) -> None:
        dialog._deal(dialog._gaps)
        application.processEvents()
        first_control = controls_as_drawn(dialog)[0]
        dialog.pages.trees[-1].setFocus(Qt.FocusReason.TabFocusReason)
        pressed(application, Qt.Key.Key_Tab)
        assert QApplication.focusWidget() is first_control


class TestInsideAList:
    def test_right_opens_an_artist_and_left_shuts_it(
        self, application: QApplication, dialog: ResultsDialog
    ) -> None:
        source = dialog.sources[0]
        source.setExpanded(False)
        standing_on(application, dialog, source)
        pressed(application, Qt.Key.Key_Right)
        assert source.isExpanded()
        pressed(application, Qt.Key.Key_Left)
        assert not source.isExpanded()
        assert QApplication.focusWidget() is dialog.pages.trees[0], "never left"

    def test_right_opens_a_similar_artist(
        self, application: QApplication, dialog: ResultsDialog
    ) -> None:
        candidate = first_candidate(dialog)
        standing_on(application, dialog, candidate)
        pressed(application, Qt.Key.Key_Right)
        assert candidate.isExpanded()

    @pytest.mark.parametrize("key", CHOOSING_KEYS)
    def test_enter_and_space_open_and_shut_an_artist(
        self, application: QApplication, dialog: ResultsDialog, key: Qt.Key
    ) -> None:
        source = dialog.sources[0]
        source.setExpanded(False)
        standing_on(application, dialog, source)
        pressed(application, key)
        assert source.isExpanded()
        pressed(application, key)
        assert not source.isExpanded()

    @pytest.mark.parametrize("key", CHOOSING_KEYS)
    def test_enter_and_space_tick_and_untick_an_album(
        self, application: QApplication, dialog: ResultsDialog, key: Qt.Key
    ) -> None:
        album = first_album(dialog)
        standing_on(application, dialog, album)
        pressed(application, key)
        assert album.checkState(0) is TICKED
        pressed(application, key)
        assert album.checkState(0) is UNTICKED
        assert dialog.isVisible(), "Enter chose the row, not the Close control"

    def test_down_reaches_an_album(
        self, application: QApplication, dialog: ResultsDialog
    ) -> None:
        standing_on(application, dialog, dialog.sources[0])
        pressed(application, Qt.Key.Key_Down)
        assert dialog.pages.trees[0].currentItem() is first_album(dialog)


def test_every_row_of_a_list_is_one_height(
    application: QApplication, dialog: ResultsDialog
) -> None:
    """Measured on 2026-09-17 on the real screen: rows of 18 and 26 pixels in
    one list, since the rows measured before the list was styled kept the
    height of an unstyled row. The ring made it plain; it was there before.

    Asked per kind of row here. Offscreen, the one fallback font is shorter
    than a tick box, so an album row stands taller than an artist row, where
    the real screen measured every row at 26. Without the fix the same run
    gives four heights, so the kinds still catch it."""
    for tree in dialog.pages.trees:
        for tickable in (True, False):
            heights = {
                tree.visualItemRect(row).height()
                for row in every_row(tree)
                if is_tickable(row) is tickable
            }
            assert len(heights) == 1, (tickable, heights)


class RecordingTicks(BoxedTicks):
    """The delegate, noting each box it draws instead of drawing it."""

    def __init__(self, parent) -> None:
        super().__init__(parent)
        self.drawn: list[bool] = []

    def draw_indicator(self, style, option, painter, view) -> None:
        self.drawn.append(bool(option.state & QStyle.StateFlag.State_On))


def test_a_ticked_album_is_drawn_boxed(
    application: QApplication, dialog: ResultsDialog
) -> None:
    """Asked for by Oliver on 2026-09-17: the platform style drew a ticked
    album as a bare tick with no box, measured on the real screen. Every list
    draws through the delegate; a ticked row gets the empty box then the tick,
    an unticked row gets nothing beyond what Qt draws."""
    for tree in dialog.pages.trees:
        assert isinstance(tree.itemDelegate(), BoxedTicks)
    tree = dialog.pages.trees[0]
    recorder = RecordingTicks(tree)
    tree.setItemDelegate(recorder)
    album = first_album(dialog)
    tree.grab()
    assert recorder.drawn == [], "nothing ticked, nothing extra drawn"
    album.setCheckState(0, TICKED)
    tree.grab()
    assert recorder.drawn[:2] == [False, True], "the box, then the tick in it"


def ring_pixels(widget, ring: str) -> int:
    """How many pixels of the ring colour the widget draws."""
    image = widget.grab().toImage()
    wanted = QColor(ring).rgb()
    return sum(
        1
        for y in range(image.height())
        for x in range(image.width())
        if image.pixel(x, y) == wanted
    )


def test_the_current_row_wears_the_ring_only_while_its_list_has_focus(
    application: QApplication, dialog: ResultsDialog
) -> None:
    """Measured before the change: a current album drew a band barely darker
    than the list and nothing round its box, which is the ticks never taking
    the focus as Oliver saw it."""
    ring = palette_for(Mode.DARK).ring
    tree = dialog.pages.trees[0]
    standing_on(application, dialog, first_album(dialog))
    focused = ring_pixels(tree, ring)
    dialog.close_button.setFocus(Qt.FocusReason.TabFocusReason)
    application.processEvents()
    assert focused > 0, "the current row is ringed while the list has focus"
    assert ring_pixels(tree, ring) == 0, "and not once the focus has gone"
