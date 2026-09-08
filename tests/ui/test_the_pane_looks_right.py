"""How the album pane is laid out and what its two controls wear.

Split from `test_rolling_the_pane_up`, which is about what a PRESS does. How
the pane looks and how it answers a press are two concerns; the file holding
both reached the danger band the line cap draws.
"""

from __future__ import annotations

from pane_support import corners, press, window
from PySide6.QtWidgets import QApplication

from stellody.shared import resources
from stellody.ui.album_pane import PANE_MARGIN_PX
from stellody.ui.bottom_tray import BOTTOM_ICON_PX
from stellody.ui.dialogs import CLOSE_ICON
from stellody.ui.icons import plain_icon
from stellody.ui.main_window import MainWindow
from stellody.ui.theme import palette_for

# The fixture is imported for pytest to find, so it is re-exported rather
# than left looking unused.
__all__ = ["window"]

# The room asked for around the text, written out here rather than read from
# the module it guards: taking both sides from one constant proves only that
# the constant equals itself.
WANTED_PAD_PX = 8


class TestWhereTheTwoButtonsSit:
    """The play and close buttons were beside the album's name, which made the
    name stop short of the edge to leave room for them. They sit under it now,
    at the end of the rating row, twice the size they were."""

    def _opened(self, window: MainWindow):
        """The pane open on the first album, laid out at a real size."""
        window.resize(1100, 800)
        press(window, 0)
        QApplication.processEvents()
        return window._album_pane

    def test_the_name_runs_to_the_end_of_the_pane(self, window: MainWindow) -> None:
        """Nothing sits beside it any more, so nothing shortens it."""
        pane = self._opened(window)
        assert pane.title.geometry().right() == pane.width() - PANE_MARGIN_PX - 1

    def test_the_buttons_sit_under_the_name(self, window: MainWindow) -> None:
        pane = self._opened(window)
        for button in (pane.play_button, pane.close_button):
            assert button.geometry().top() >= pane.artist.geometry().bottom()

    def test_the_close_button_wears_the_close_picture(self, window: MainWindow) -> None:
        """Not the negative mark, which says a switch is off rather than what
        a press does. Every other Close in the application wears this."""
        pane = self._opened(window)
        drawn = pane.close_button.icon().pixmap(BOTTOM_ICON_PX, BOTTOM_ICON_PX)
        expected = plain_icon(resources.find_asset(CLOSE_ICON)).pixmap(
            BOTTOM_ICON_PX, BOTTOM_ICON_PX
        )
        assert bytes(drawn.toImage().constBits()) == bytes(
            expected.toImage().constBits()
        )
        negative = plain_icon(resources.negative_icon_path()).pixmap(
            BOTTOM_ICON_PX, BOTTOM_ICON_PX
        )
        assert bytes(drawn.toImage().constBits()) != bytes(
            negative.toImage().constBits()
        )

    def test_the_last_button_is_flush_with_the_edge(self, window: MainWindow) -> None:
        """Right justified, so the pair reads as belonging to the row's end."""
        pane = self._opened(window)
        assert pane.close_button.geometry().right() == pane.width() - PANE_MARGIN_PX - 1
        assert pane.play_button.geometry().right() < pane.close_button.geometry().left()

    # The size asked for, written out here rather than read from the module it
    # is guarding. Taking both sides from the one constant proved only that the
    # constant equals itself: planting sixteen back left the test passing.
    WANTED_ICON_PX = 32

    def test_the_pictures_are_drawn_at_twice_the_old_size(
        self, window: MainWindow
    ) -> None:
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

    def _opened(self, window: MainWindow):
        window.resize(900, 800)
        press(window, 0)
        QApplication.processEvents()
        return window._album_pane

    def _labels(self, pane):
        return (pane.title, pane.artist, pane.rating_caption)

    def test_the_text_is_held_off_both_edges(self, window: MainWindow) -> None:
        """contentsRect is where the text may go, once padding is taken out."""
        for label in self._labels(self._opened(window)):
            whole, inside = label.rect(), label.contentsRect()
            assert inside.left() - whole.left() >= WANTED_PAD_PX
            assert whole.right() - inside.right() >= WANTED_PAD_PX

    def test_the_caption_rounds_on_all_fourcorners(self, window: MainWindow) -> None:
        """The pane's own colour showing at a corner is the rounding."""
        pane = self._opened(window)
        painted = pane.grab().toImage()
        behind = palette_for(pane._mode).surface_alt
        for spot in corners(pane.rating_caption.geometry()):
            assert painted.pixelColor(*spot).name() == behind

    def test_the_name_and_the_artist_round_only_on_the_outside(
        self, window: MainWindow
    ) -> None:
        """They read as one block, so rounding each in full would pinch the
        join between them into an hourglass. The title takes the top corners,
        the artist the bottom; the two edges that meet stay square."""
        pane = self._opened(window)
        painted = pane.grab().toImage()
        behind = palette_for(pane._mode).surface_alt
        top_left, top_right, low_left, low_right = corners(pane.title.geometry())
        assert painted.pixelColor(*top_left).name() == behind
        assert painted.pixelColor(*top_right).name() == behind
        assert painted.pixelColor(*low_left).name() != behind
        assert painted.pixelColor(*low_right).name() != behind
        top_left, top_right, low_left, low_right = corners(pane.artist.geometry())
        assert painted.pixelColor(*low_left).name() == behind
        assert painted.pixelColor(*low_right).name() == behind
        assert painted.pixelColor(*top_left).name() != behind
        assert painted.pixelColor(*top_right).name() != behind
