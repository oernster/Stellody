"""The grid of tick boxes an album's genres are chosen from.

What is settled here is what the grid offers, what it starts ticked and what it
answers when asked. That an album can carry several is the whole reason it is a
grid rather than a line to type in.
"""

from __future__ import annotations

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from stellody.domain.genres import CATALOGUE, GENRES, MAIN_OF
from stellody.ui.genre_grid import (
    COLUMNS,
    UNSTATED,
    GenreGrid,
    dealt_into_columns,
)
from stellody.ui.ringed_check import RingedCheckBox


@pytest.fixture
def grid(application: QApplication):
    def opened(value: str = "") -> GenreGrid:
        return GenreGrid(value)

    return opened


class TestWhatItOffers:
    def test_every_genre_in_the_catalogue_has_a_box(self, grid) -> None:
        chooser = grid()
        assert sorted(chooser.boxes) == sorted(GENRES)

    def test_it_is_laid_out_in_the_columns_that_were_settled(self, grid) -> None:
        """Three, measured: two made the album panel 852 pixels tall."""
        chooser = grid()
        assert chooser.layout().itemAt(1).layout().count() == COLUMNS

    def test_every_group_stays_whole_and_in_catalogue_order(self) -> None:
        """A main and its styles are read together, so a group is never
        split across a column boundary."""
        dealt = dealt_into_columns(CATALOGUE, COLUMNS)
        placed = [main for column in dealt for main, _styles in column]
        assert sorted(placed) == sorted(main for main, _s in CATALOGUE)
        order = [main for main, _styles in CATALOGUE]
        for column in dealt:
            where = [order.index(main) for main, _styles in column]
            assert where == sorted(where)

    def test_the_columns_are_dealt_by_height_not_in_order(self) -> None:
        """Electronic carries eleven styles while four mains carry none,
        so filling one column then the next leaves one twice the other."""
        heights = [
            sum(1 + len(styles) for _main, styles in column)
            for column in dealt_into_columns(CATALOGUE, COLUMNS)
        ]
        tallest = max(1 + len(styles) for _main, styles in CATALOGUE)
        assert max(heights) - min(heights) <= tallest

    def test_exactly_one_ampersand_reaches_the_screen(self, grid) -> None:
        """Never two drawn; never a shortcut quietly taken either.

        Qt reads a single ampersand in a control's text as the marker before a
        shortcut key, so the doubled form is how a literal one is asked for.
        The doubling is what the SOURCE says, never what a person sees.

        Measured separately, on this venv: left unescaped, `Drum & Bass` draws
        at the width of `Drum  Bass` and takes Alt+Space, which is Windows' own
        system menu, while `R&B & Soul` takes Alt+B. Escaped, both draw at the
        width of the name as written and take nothing. Neither is a catalogue
        name any more; Contemporary R&B is the one that still holds one, so it
        is the one asked here.
        """
        chooser = grid()
        for name in ("Contemporary R&B",):
            box = chooser.boxes[name]
            # The escaped source is what asks Qt for a literal ampersand.
            assert box.text() == name.replace("&", "&&")
            # No shortcut taken, which is Qt's own signal that no ampersand
            # was read as a marker, so each is drawn rather than eaten.
            assert box.shortcut().toString() == ""
            # Wider than the same name left unescaped, because that form
            # loses a character to the marker. Compared against a control
            # rather than against an absolute width: Qt ships no fonts here,
            # so the fallback differs between runs and any exact figure is a
            # measurement of the font rather than of the escaping.
            unescaped = RingedCheckBox(name, chooser)
            assert box.sizeHint().width() > unescaped.sizeHint().width()
            assert unescaped.shortcut().toString() != ""

    def test_a_name_holding_no_ampersand_needs_no_escaping(self, grid) -> None:
        # Held in a name: a parentless widget nothing refers to is collected
        # the moment the expression ends, taking its boxes with it.
        chooser = grid()
        assert chooser.boxes["Rock"].text() == "Rock"
        assert chooser.boxes["Rock"].shortcut().toString() == ""

    def test_the_grid_itself_is_not_a_stop_on_the_keyboard_ring(self, grid) -> None:
        """A ring belongs to the controls, never to what holds them."""
        chooser = grid()
        assert chooser.focusPolicy() is Qt.FocusPolicy.NoFocus


class TestWhatItStartsWith:
    def test_nothing_is_ticked_for_an_album_stating_no_genre(self, grid) -> None:
        chooser = grid("")
        assert chooser.chosen() == ()
        assert chooser.text() == ""

    def test_a_matching_tag_starts_ticked(self, grid) -> None:
        chooser = grid("Rock")
        assert chooser.chosen() == ("Rock",)

    def test_case_is_ignored_when_deciding_what_is_ticked(self, grid) -> None:
        """The library holds both `Pop` and `pop`, measured."""
        chooser = grid("pop")
        assert chooser.chosen() == ("Pop",)

    def test_several_genres_start_ticked(self, grid) -> None:
        chooser = grid("Rock; Alternative")
        assert chooser.chosen() == ("Rock", "Alternative Rock")

    def test_a_style_starts_its_main_ticked_too(self, grid) -> None:
        """The value it would answer with holds both, so the boxes do."""
        chooser = grid("Trance")
        assert chooser.chosen() == ("Electronic", "Trance")

    def test_a_tag_naming_two_things_ticks_both(self, grid) -> None:
        """`Hip-Hop/Rap` is one tag holding two names, measured."""
        chooser = grid("Jazz/Blues")
        assert chooser.chosen() == ("Blues", "Jazz")


class TestWhatItSaysAboutATagItCannotMatch:
    def test_an_unmatched_tag_is_shown_rather_than_hidden(self, grid) -> None:
        """Otherwise the panel shows no box ticked and says nothing at all.

        No tag in the reference library reaches nothing any more, so this
        asks with one the library does not carry: a genre is stated by a
        ruling, so a library those rulings have not met yet is the ordinary
        case for anyone but this library's owner.
        """
        chooser = grid("Progressive Rock")
        assert chooser.aside.isVisibleTo(chooser)
        assert "Progressive Rock" in chooser.aside.text()

    def test_nothing_is_said_where_the_tag_matched(self, grid) -> None:
        chooser = grid("Rock")
        assert not chooser.aside.isVisibleTo(chooser)
        assert chooser.aside.text() == ""

    def test_an_album_stating_no_genre_is_told_so(self, grid) -> None:
        """An empty grid otherwise means two things and looks the same in both:
        nothing to show; something shown that no box could hold. Silence in
        the first case reads as a defect, which is how this came to be asked
        for: a cue-ripped album whose FLAC carries no genre tag at all."""
        chooser = grid("")
        assert chooser.aside.isVisibleTo(chooser)
        assert chooser.aside.text() == UNSTATED

    def test_whitespace_alone_is_not_a_tag(self, grid) -> None:
        chooser = grid("   ")
        assert chooser.aside.text() == UNSTATED

    def test_the_two_asides_never_say_the_same_thing(self, grid) -> None:
        """Telling them apart is the whole point of having two."""
        silent = grid("")
        unmatched = grid("Progressive Rock")
        assert silent.aside.text() != unmatched.aside.text()


class TestWhatItAnswers:
    def test_it_answers_as_a_line_edit_does(self, grid) -> None:
        """The panel holds it beside the lines and asks all of them `text()`."""
        chooser = grid()
        chooser.boxes["Heavy Metal"].setChecked(True)
        assert chooser.text() == "Rock; Heavy Metal"

    def test_what_is_answered_is_in_catalogue_order(self, grid) -> None:
        chooser = grid()
        chooser.boxes["World"].setChecked(True)
        chooser.boxes["Blues"].setChecked(True)
        assert chooser.text() == "Blues; World"

    def test_unticking_what_a_tag_started_with_states_nothing(self, grid) -> None:
        chooser = grid("Rock")
        chooser.boxes["Rock"].setChecked(False)
        assert chooser.text() == ""

    def test_an_album_can_carry_a_genre_its_tag_never_named(self, grid) -> None:
        """The Green Day case: tagged Rock alone and plainly Punk as well.
        Punk is a main of its own, so this states two of them side by side."""
        chooser = grid("Rock")
        chooser.boxes["Punk"].setChecked(True)
        assert chooser.text() == "Punk; Rock"


class TestTheTwoLevelsAgreeingWithEachOther:
    """A style states its main, so the boxes cannot say otherwise."""

    def test_ticking_a_style_ticks_its_main(self, grid) -> None:
        chooser = grid()
        chooser.boxes["Trance"].setChecked(True)
        assert chooser.boxes["Electronic"].isChecked()
        assert chooser.text() == "Electronic; Trance"

    def test_clearing_a_main_clears_its_styles(self, grid) -> None:
        """An album that is not electronic is not trance either."""
        chooser = grid("Trance")
        chooser.boxes["Electronic"].setChecked(False)
        assert not chooser.boxes["Trance"].isChecked()
        assert chooser.text() == ""

    def test_clearing_a_style_leaves_its_main_alone(self, grid) -> None:
        """Deliberately not the mirror image: the album may still be
        electronic after somebody decides it is not specifically trance."""
        chooser = grid("Trance")
        chooser.boxes["Trance"].setChecked(False)
        assert chooser.boxes["Electronic"].isChecked()
        assert chooser.text() == "Electronic"

    def test_clearing_a_main_leaves_another_main_alone(self, grid) -> None:
        chooser = grid("Trance; Pop")
        chooser.boxes["Electronic"].setChecked(False)
        assert chooser.boxes["Pop"].isChecked()
        assert chooser.text() == "Pop"

    def test_every_style_is_drawn_in_from_its_main(self, grid) -> None:
        """Indented rather than merely listed, so the two levels are
        visible rather than something the reader has to know."""
        chooser = grid()
        columns = chooser.layout().itemAt(1).layout()
        indented = set()
        for index in range(columns.count()):
            stack = columns.itemAt(index).layout()
            for row in range(stack.count()):
                nested = stack.itemAt(row).layout()
                if nested is None:
                    continue
                for held in range(nested.count()):
                    widget = nested.itemAt(held).widget()
                    if widget is not None:
                        indented.add(widget.text().replace("&&", "&"))
        assert indented == set(MAIN_OF)


def test_every_box_carries_the_house_ring(application: QApplication) -> None:
    """A checkbox is a stop on the keyboard ring, so it paints one.

    The structural suite forbids a plain QCheckBox anywhere in the package;
    this says the same thing about this grid in particular, in terms of what
    a listener would see rather than of what the source imports.
    """
    chooser = GenreGrid("")
    for name, box in chooser.boxes.items():
        assert isinstance(box, RingedCheckBox), name
