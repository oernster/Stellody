"""The genre grid's categories folding their styles away.

Ruled by Oliver on 2026-10-01: three columns; every category starts folded;
what was open is remembered for each dialog holding the grid; a folded
category holding ticked styles says how many beside its name.
"""

from __future__ import annotations

import pytest
from PySide6.QtCore import QPoint, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from tray_support import RememberingStore

from stellody.domain.genres import CATALOGUE, MAIN_OF, MAINS
from stellody.ui import settings_keys
from stellody.ui.filter_dialog import FilterDialog
from stellody.ui.genre_folds import Folds
from stellody.ui.genre_grid import GenreGrid
from stellody.ui.genre_group import FOLDED_GLYPH, OPEN_GLYPH
from stellody.ui.results_filter import ResultsFilterDialog
from stellody.ui.ring import next_stop

KEY = "genres_open_test"
# Mains with styles to fold and one with none, read off the catalogue.
WITH_STYLES = next(main for main, styles in CATALOGUE if styles)
WITHOUT_STYLES = next(main for main, styles in CATALOGUE if not styles)


def _first_style(main: str) -> str:
    return next(style for style, held in MAIN_OF.items() if held == main)


@pytest.fixture
def store() -> RememberingStore:
    return RememberingStore()


@pytest.fixture
def grid(application: QApplication, store: RememberingStore):
    def opened(value: str = "") -> GenreGrid:
        return GenreGrid(value, folds=Folds(store, KEY))

    return opened


class TestFoldedByDefault:
    def test_every_category_starts_folded(self, grid) -> None:
        chooser = grid()
        assert not any(group.is_open() for group in chooser.groups.values())

    def test_a_folded_style_is_not_on_screen(self, grid) -> None:
        chooser = grid()
        style = _first_style(WITH_STYLES)
        assert not chooser.boxes[style].isVisibleTo(chooser)

    def test_every_main_is_on_screen(self, grid) -> None:
        chooser = grid()
        assert all(chooser.boxes[main].isVisibleTo(chooser) for main in MAINS)

    def test_a_grid_with_no_memory_starts_folded_too(self, application) -> None:
        chooser = GenreGrid("")
        assert not any(group.is_open() for group in chooser.groups.values())


class TestTheArrow:
    def test_pressing_it_shows_the_styles(self, grid) -> None:
        chooser = grid()
        group = chooser.groups[WITH_STYLES]
        group.arrow.click()
        assert group.is_open()
        assert chooser.boxes[_first_style(WITH_STYLES)].isVisibleTo(chooser)

    def test_pressing_it_again_folds_them(self, grid) -> None:
        chooser = grid()
        group = chooser.groups[WITH_STYLES]
        group.arrow.click()
        group.arrow.click()
        assert not chooser.boxes[_first_style(WITH_STYLES)].isVisibleTo(chooser)

    def test_it_points_the_way_the_category_is(self, grid) -> None:
        chooser = grid()
        group = chooser.groups[WITH_STYLES]
        assert group.arrow.text() == FOLDED_GLYPH
        group.set_open(True)
        assert group.arrow.text() == OPEN_GLYPH

    def test_a_main_with_no_styles_offers_no_arrow(self, grid) -> None:
        chooser = grid()
        assert chooser.groups[WITHOUT_STYLES].arrow.isHidden()

    def test_every_main_box_starts_at_the_same_place(self, grid) -> None:
        """A main with no arrow keeps its room, so the column lines up."""
        chooser = grid()
        chooser.show()
        with_x = chooser.boxes[WITH_STYLES].mapTo(chooser, QPoint()).x()
        group_x = chooser.groups[WITH_STYLES].mapTo(chooser, QPoint()).x()
        bare = chooser.groups[WITHOUT_STYLES]
        bare_x = chooser.boxes[WITHOUT_STYLES].mapTo(chooser, QPoint()).x()
        assert with_x - group_x == bare_x - bare.mapTo(chooser, QPoint()).x()


class TestTheCountBesideAFoldedMain:
    def test_a_ticked_style_folded_away_is_counted(self, grid) -> None:
        chooser = grid()
        chooser.boxes[_first_style(WITH_STYLES)].setChecked(True)
        assert chooser.groups[WITH_STYLES].count.text() == "(1)"

    def test_nothing_is_counted_while_the_styles_show(self, grid) -> None:
        chooser = grid()
        chooser.boxes[_first_style(WITH_STYLES)].setChecked(True)
        chooser.groups[WITH_STYLES].set_open(True)
        assert chooser.groups[WITH_STYLES].count.text() == ""

    def test_nothing_ticked_says_nothing(self, grid) -> None:
        chooser = grid()
        assert all(group.count.text() == "" for group in chooser.groups.values())

    def test_a_value_opened_with_counts_what_it_holds(self, grid) -> None:
        """An album tagged Dubstep shows Electronic ticked and (1) beside it."""
        chooser = grid("Dubstep")
        assert chooser.groups["Electronic"].count.text() == "(1)"


class TestRemembered:
    def test_opening_a_category_is_kept(self, grid, store) -> None:
        grid().groups[WITH_STYLES].set_open(True)
        assert store.settings[KEY] == WITH_STYLES

    def test_the_next_grid_opens_what_was_left_open(self, grid) -> None:
        grid().groups[WITH_STYLES].set_open(True)
        assert grid().groups[WITH_STYLES].is_open()

    def test_folding_it_again_is_kept_too(self, grid) -> None:
        first = grid()
        first.groups[WITH_STYLES].set_open(True)
        first.groups[WITH_STYLES].set_open(False)
        assert not grid().groups[WITH_STYLES].is_open()

    def test_a_name_no_longer_a_main_is_passed_over(self, store) -> None:
        store.settings[KEY] = f"Nonsense; {WITH_STYLES}"
        assert Folds(store, KEY).opened() == frozenset({WITH_STYLES})

    def test_it_is_kept_in_catalogue_order(self, store) -> None:
        folds = Folds(store, KEY)
        folds.keep(reversed(MAINS[:2]))
        assert store.settings[KEY] == "; ".join(MAINS[:2])

    def test_each_dialog_remembers_on_its_own(self) -> None:
        keys = {
            settings_keys.SETTING_GENRES_OPEN_DISCOVERY,
            settings_keys.SETTING_GENRES_OPEN_LIBRARY_FILTER,
            settings_keys.SETTING_GENRES_OPEN_ANSWER_FILTER,
            settings_keys.SETTING_GENRES_OPEN_TAG_EDITOR,
        }
        assert len(keys) == 4


class TestOnTheKeyboard:
    """The arrow is a stop just before its main; folded styles are not."""

    @pytest.fixture
    def shown(self, application, store):
        dialog = FilterDialog(folds=Folds(store, KEY))
        dialog.show()
        yield dialog
        dialog.close()

    def test_the_arrow_comes_just_before_its_main(self, shown) -> None:
        group = shown.grid.groups[WITH_STYLES]
        assert next_stop(group.arrow, True) is group.box

    def test_a_folded_category_is_left_in_one_step(self, shown) -> None:
        group = shown.grid.groups[WITH_STYLES]
        after = next_stop(group.box, True)
        assert after not in group.style_boxes

    def test_an_open_category_leads_into_its_styles(self, shown) -> None:
        group = shown.grid.groups[WITH_STYLES]
        group.set_open(True)
        assert next_stop(group.box, True) is group.style_boxes[0]

    def test_space_on_the_arrow_opens_it(self, shown) -> None:
        group = shown.grid.groups[WITH_STYLES]
        group.arrow.setFocus(Qt.FocusReason.TabFocusReason)
        QTest.keyClick(group.arrow, Qt.Key.Key_Space)
        assert group.is_open()

    def test_enter_on_the_arrow_opens_it_rather_than_the_dialog(self, shown) -> None:
        group = shown.grid.groups[WITH_STYLES]
        group.arrow.setFocus(Qt.FocusReason.TabFocusReason)
        QTest.keyClick(group.arrow, Qt.Key.Key_Return)
        assert group.is_open()
        assert shown.isVisible()


class TestInTheAnswersFilter:
    """Only the genres a run looked in are offered there. FR-D54."""

    def test_a_category_with_nothing_on_offer_is_not_shown(self, application):
        style = _first_style(WITH_STYLES)
        dialog = ResultsFilterDialog((WITH_STYLES, style))
        assert dialog.grid.groups[WITH_STYLES].isVisibleTo(dialog)
        assert not dialog.grid.groups[WITHOUT_STYLES].isVisibleTo(dialog)

    def test_a_main_offered_without_its_styles_has_no_arrow(self, application):
        dialog = ResultsFilterDialog((WITH_STYLES,))
        assert dialog.grid.groups[WITH_STYLES].arrow.isHidden()

    def test_a_style_offered_without_its_main_still_opens(self, application):
        """Its main's box is hidden, the arrow is not: the style is the offer."""
        dialog = ResultsFilterDialog((_first_style(WITH_STYLES),))
        group = dialog.grid.groups[WITH_STYLES]
        assert not group.arrow.isHidden()
        assert group.isVisibleTo(dialog)


def test_folding_gives_the_room_back(application, store) -> None:
    """A dialog grows to hold an open category, then shrinks again, at once:
    no pass of the event loop is waited for. A version that waited one pass
    passed alone and failed in the full suite."""
    dialog = FilterDialog(folds=Folds(store, KEY))
    dialog.show()
    folded = dialog.height()
    group = dialog.grid.groups[WITH_STYLES]
    group.set_open(True)
    assert dialog.height() > folded
    group.set_open(False)
    assert dialog.height() == folded
    dialog.close()
