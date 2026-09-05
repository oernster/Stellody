"""Pressing a sleeve a second time rolls the album pane back up.

The gesture that opened the pane is the one asked to undo it. The pane's own
close button did this from the start, at the size the tray draws its buttons
and wearing the mark the mute switch uses, which is not a way down anybody
found.

Every test here presses the real viewport rather than calling the handler.
That is the whole point: Qt moves the current index during the PRESS, so a
first press on a fresh sleeve and a second press on the open one are told
apart only by reading the press itself. Calling the handler proves nothing
about which of them arrives.
"""

from __future__ import annotations

import pytest
from conftest import RecordingPlayer
from PySide6.QtCore import QEvent, QModelIndex, Qt
from PySide6.QtGui import QFocusEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from tray_support import RememberingStore, build, track

from stellody.domain.album import Album
from stellody.domain.identity import AlbumIdentity
from stellody.ui.album_pane import PANE_MARGIN_PX
from stellody.ui.row_text import Column
from stellody.ui.theme import palette_for

LEFT = Qt.MouseButton.LeftButton
RIGHT = Qt.MouseButton.RightButton
# The room asked for around the text, written out here rather than read from
# the module it guards: taking both sides from one constant proves only that
# the constant equals itself.
WANTED_PAD_PX = 8


def _corners(box) -> tuple[tuple[int, int], ...]:
    """The four corner pixels of a rectangle, clockwise from the top left."""
    return (
        (box.left(), box.top()),
        (box.right(), box.top()),
        (box.left(), box.bottom()),
        (box.right(), box.bottom()),
    )


@pytest.fixture
def window(application: QApplication):
    """A real window showing the sleeves of two albums."""
    made = build(RememberingStore(), RecordingPlayer())
    made._model.set_albums(
        (
            Album(
                identity=AlbumIdentity(album_artist="Holst", title="Alpha"),
                tracks=(track(1), track(2)),
            ),
            Album(
                identity=AlbumIdentity(album_artist="Holst", title="Beta"),
                tracks=(track(1), track(2)),
            ),
        )
    )
    made.resize(1400, 900)
    made.show()
    made.toggle_view()
    yield made
    made.close()


def _hand_focus_back(window, reason: Qt.FocusReason) -> None:
    """Give the grid focus the way the toolkit does when something closes."""
    window._grid.clearFocus()
    window._grid.selectionModel().clearCurrentIndex()
    QApplication.processEvents()
    QApplication.sendEvent(window._grid, QFocusEvent(QEvent.Type.FocusIn, reason))
    QApplication.processEvents()


def press(window, row: int, button: Qt.MouseButton = LEFT) -> None:
    """Press the sleeve in that row, as a listener does."""
    where = window._model.index(row, Column.TITLE, QModelIndex())
    QTest.mouseClick(
        window._grid.viewport(),
        button,
        pos=window._grid.visualRect(where).center(),
    )


class TestPressingASleeveTwice:
    def test_the_first_press_opens_the_pane(self, window) -> None:
        press(window, 0)
        assert window._album_pane.isVisible()
        assert window._album_pane.title.text() == "Alpha"

    def test_the_second_press_rolls_it_back_up(self, window) -> None:
        press(window, 0)
        press(window, 0)
        assert not window._album_pane.isVisible()

    def test_a_third_press_opens_it_again(self, window) -> None:
        """The sleeve used to go dead: it was still current, so nothing changed."""
        press(window, 0)
        press(window, 0)
        press(window, 0)
        assert window._album_pane.isVisible()

    def test_pressing_another_sleeve_switches_rather_than_shuts(self, window) -> None:
        press(window, 0)
        press(window, 1)
        assert window._album_pane.isVisible()
        assert window._album_pane.title.text() == "Beta"

    def test_pressing_past_the_last_sleeve_leaves_the_pane_alone(self, window) -> None:
        """Empty space is not a sleeve, so it says nothing about the pane."""
        press(window, 0)
        QTest.mouseClick(
            window._grid.viewport(), LEFT, pos=window._grid.rect().bottomRight()
        )
        assert window._album_pane.isVisible()


class TestTheOtherWaysDown:
    def test_the_close_button_still_shuts_it(self, window) -> None:
        press(window, 0)
        window._album_pane.close_button.click()
        assert not window._album_pane.isVisible()

    def test_a_sleeve_closed_that_way_opens_on_the_next_press(self, window) -> None:
        press(window, 0)
        window._album_pane.close_button.click()
        press(window, 0)
        assert window._album_pane.isVisible()

    def test_moving_the_selection_still_opens_the_pane(self, window) -> None:
        """Keyboard reach does not go through a press at all."""
        window._grid.setCurrentIndex(
            window._model.index(1, Column.TITLE, QModelIndex())
        )
        assert window._album_pane.isVisible()
        assert window._album_pane.title.text() == "Beta"


class TestTheHighlightIsNotDisturbed:
    def test_reopening_the_album_already_open_leaves_the_choice_alone(
        self, window
    ) -> None:
        """A press and the selection change it causes both ask to open it."""
        press(window, 0)
        pane = window._album_pane
        album = window._model.album_at(
            window._model.index(0, Column.TITLE, QModelIndex())
        )
        second = window._model.index_for(album.ordered_tracks()[1])
        pane.columns[1].setCurrentIndex(second)
        window.open_album_at(window._model.index(0, Column.TITLE, QModelIndex()))
        assert window._model.track_at(pane.current_index()).track_number == 2


class TestWhereTheTwoButtonsSit:
    """The play and close buttons were beside the album's name, which made the
    name stop short of the edge to leave room for them. They sit under it now,
    at the end of the rating row, twice the size they were."""

    def _opened(self, window):
        """The pane open on the first album, laid out at a real size."""
        window.resize(1100, 800)
        press(window, 0)
        QApplication.processEvents()
        return window._album_pane

    def test_the_name_runs_to_the_end_of_the_pane(self, window) -> None:
        """Nothing sits beside it any more, so nothing shortens it."""
        pane = self._opened(window)
        assert pane.title.geometry().right() == pane.width() - PANE_MARGIN_PX - 1

    def test_the_buttons_sit_under_the_name(self, window) -> None:
        pane = self._opened(window)
        for button in (pane.play_button, pane.close_button):
            assert button.geometry().top() >= pane.artist.geometry().bottom()

    def test_the_last_button_is_flush_with_the_edge(self, window) -> None:
        """Right justified, so the pair reads as belonging to the row's end."""
        pane = self._opened(window)
        assert pane.close_button.geometry().right() == pane.width() - PANE_MARGIN_PX - 1
        assert pane.play_button.geometry().right() < pane.close_button.geometry().left()

    # The size asked for, written out here rather than read from the module it
    # is guarding. Taking both sides from the one constant proved only that the
    # constant equals itself: planting sixteen back left the test passing.
    WANTED_ICON_PX = 32

    def test_the_pictures_are_drawn_at_twice_the_old_size(self, window) -> None:
        """Sixteen was too small to read at the end of the row."""
        pane = self._opened(window)
        for button in (pane.play_button, pane.close_button):
            assert button.iconSize().width() == self.WANTED_ICON_PX
            assert button.width() > self.WANTED_ICON_PX


class TestTheHeaderTextIsNotAgainstItsEdges:
    """Every widget is filled by the blanket rule, so a label in this header
    reads as a rectangle whether or not anybody meant it to. The three that do
    are given room around the text and the house radius, rather than being left
    as hard boxes with the first letter against the corner.

    Measured from what Qt actually laid out and painted, never from the style
    sheet's text: a rule that never reached the widget reads identically to one
    that did.
    """

    def _opened(self, window):
        window.resize(900, 800)
        press(window, 0)
        QApplication.processEvents()
        return window._album_pane

    def _labels(self, pane):
        return (pane.title, pane.artist, pane.rating_caption)

    def test_the_text_is_held_off_both_edges(self, window) -> None:
        """contentsRect is where the text may go, once padding is taken out."""
        for label in self._labels(self._opened(window)):
            whole, inside = label.rect(), label.contentsRect()
            assert inside.left() - whole.left() >= WANTED_PAD_PX
            assert whole.right() - inside.right() >= WANTED_PAD_PX

    def test_the_caption_rounds_on_all_four_corners(self, window) -> None:
        """The pane's own colour showing at a corner is the rounding."""
        pane = self._opened(window)
        painted = pane.grab().toImage()
        behind = palette_for(pane._mode).surface_alt
        for spot in _corners(pane.rating_caption.geometry()):
            assert painted.pixelColor(*spot).name() == behind

    def test_the_name_and_the_artist_round_only_on_the_outside(self, window) -> None:
        """They read as one block, so rounding each in full would pinch the
        join between them into an hourglass. The title takes the top corners,
        the artist the bottom; the two edges that meet stay square."""
        pane = self._opened(window)
        painted = pane.grab().toImage()
        behind = palette_for(pane._mode).surface_alt
        top_left, top_right, low_left, low_right = _corners(pane.title.geometry())
        assert painted.pixelColor(*top_left).name() == behind
        assert painted.pixelColor(*top_right).name() == behind
        assert painted.pixelColor(*low_left).name() != behind
        assert painted.pixelColor(*low_right).name() != behind
        top_left, top_right, low_left, low_right = _corners(pane.artist.geometry())
        assert painted.pixelColor(*low_left).name() == behind
        assert painted.pixelColor(*low_right).name() == behind
        assert painted.pixelColor(*top_left).name() != behind
        assert painted.pixelColor(*top_right).name() != behind


class TestTheRightButtonLeavesThePaneAlone:
    """A right press is somebody reaching for the sleeve's menu.

    Rolling the pane up under them takes away the album they are pointing at
    as they point at it, which is what it did: the press filter read every
    button rather than the left one.
    """

    def test_a_right_press_on_the_open_sleeve_keeps_it_open(self, window) -> None:
        press(window, 0)
        press(window, 0, RIGHT)
        assert window._album_pane.isVisible()
        assert window._album_pane.title.text() == "Alpha"

    def test_a_left_press_still_rolls_it_up_afterwards(self, window) -> None:
        """The right press must not have consumed the gesture either."""
        press(window, 0)
        press(window, 0, RIGHT)
        press(window, 0)
        assert not window._album_pane.isVisible()

    def test_a_right_press_on_another_sleeve_leaves_the_open_one(self, window) -> None:
        """Reaching for a menu is not asking to see a different album."""
        press(window, 0)
        press(window, 1, RIGHT)
        assert window._album_pane.isVisible()
        assert window._album_pane.title.text() == "Alpha"

    def test_a_right_press_on_a_shut_pane_leaves_it_shut(self, window) -> None:
        """Nothing was on show, so the menu brings nothing out with it."""
        press(window, 0, RIGHT)
        assert not window._album_pane.isVisible()

    def test_a_right_press_never_opens_and_shuts_in_one(self, window) -> None:
        """Two right presses in a row are still not a toggle."""
        press(window, 0)
        press(window, 0, RIGHT)
        press(window, 0, RIGHT)
        assert window._album_pane.isVisible()


class TestBeingHandedFocusBackLeavesThePlaceAlone:
    """What the right press exposed, one step further along.

    A view holding no current item gives the place to its first one as soon as
    focus arrives by any route other than the mouse. The right press is taken
    and dropped, so no sleeve is current; whatever that press opens then takes
    focus. Handing it back put the place on the top of the library. In the
    built application that read as the first album highlighting itself, with
    its pane opening, while the sleeve actually pointed at was left alone.

    Two ways out were met in turn, a menu and then the tag editor, so the
    reasons are asked about by name here. The platform's own window activation
    cannot be raised offscreen, which is why each is sent rather than staged:
    a dialog hands focus back as ActiveWindow and a menu as Popup. Both were
    measured inventing row 0 before this was fixed.
    """

    def _menu_and_back(self, window, row: int) -> None:
        """Right press a sleeve, take the menu it asks for, then dismiss it."""
        press(window, row, RIGHT)
        window.show_transport_menu(
            window._grid.visualRect(
                window._model.index(row, Column.TITLE, QModelIndex())
            ).center(),
            window._grid,
        )
        window._menu.close()
        QApplication.sendEvent(
            window._grid,
            QFocusEvent(QEvent.Type.FocusIn, Qt.FocusReason.PopupFocusReason),
        )
        QApplication.processEvents()

    def test_the_first_sleeve_is_not_given_the_place(self, window) -> None:
        self._menu_and_back(window, 1)
        assert not window._grid.currentIndex().isValid()

    def test_the_pane_stays_shut(self, window) -> None:
        """The invented place opened an album nobody chose."""
        self._menu_and_back(window, 1)
        assert not window._album_pane.isVisible()

    def test_the_left_press_after_it_opens_what_it_lands_on(self, window) -> None:
        self._menu_and_back(window, 1)
        press(window, 1)
        assert window._album_pane.isVisible()
        assert window._album_pane.title.text() == "Beta"

    @pytest.mark.parametrize(
        "reason",
        (
            Qt.FocusReason.PopupFocusReason,
            Qt.FocusReason.ActiveWindowFocusReason,
            Qt.FocusReason.OtherFocusReason,
        ),
        ids=("a menu closing", "a dialog closing", "anything else"),
    )
    def test_no_way_of_being_handed_focus_takes_a_sleeve(self, window, reason) -> None:
        """The rule is the ways in that ARE a choice, not a list of doors."""
        _hand_focus_back(window, reason)
        assert not window._grid.currentIndex().isValid()
        assert not window._album_pane.isVisible()

    @pytest.mark.parametrize(
        "reason",
        (Qt.FocusReason.TabFocusReason, Qt.FocusReason.BacktabFocusReason),
        ids=("tab", "shift tab"),
    )
    def test_focus_arriving_by_keyboard_still_finds_a_sleeve(
        self, window, reason
    ) -> None:
        """Reaching the grid by key is asking for a place in it, which is the
        one arrival that still gets one."""
        _hand_focus_back(window, reason)
        assert window._grid.currentIndex().isValid()
