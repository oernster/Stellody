"""The grid of tick boxes an album's genres are chosen from.

What is settled here is what the grid offers, what it starts ticked and what it
answers when asked. That an album can carry several is the whole reason it is a
grid rather than a line to type in.
"""

from __future__ import annotations

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from stellody.domain.genres import GENRES
from stellody.ui.genre_grid import COLUMNS, UNSTATED, GenreGrid
from stellody.ui.ringed_check import RingedCheckBox


@pytest.fixture
def grid(application: QApplication):
    def opened(value: str = "") -> GenreGrid:
        return GenreGrid(value)

    return opened


class TestWhatItOffers:
    def test_every_genre_in_the_catalogue_has_a_box(self, grid) -> None:
        chooser = grid()
        assert tuple(chooser.boxes) == GENRES

    def test_it_is_laid_out_in_two_columns(self, grid) -> None:
        """Eighteen names cost nine rows rather than eighteen."""
        chooser = grid()
        columns = {
            chooser.layout().itemAt(1).layout().indexOf(box) % COLUMNS
            for box in chooser.boxes.values()
        }
        assert columns == {0, 1}

    def test_exactly_one_ampersand_reaches_the_screen(self, grid) -> None:
        """Never two drawn; never a shortcut quietly taken either.

        Qt reads a single ampersand in a control's text as the marker before a
        shortcut key, so the doubled form is how a literal one is asked for.
        The doubling is what the SOURCE says, never what a person sees.

        Measured separately, on this venv: left unescaped, `Drum & Bass` draws
        at the width of `Drum  Bass` and takes Alt+Space, which is Windows' own
        system menu, while `R&B & Soul` takes Alt+B. Escaped, both draw at the
        width of the name as written and take nothing.
        """
        chooser = grid()
        for name in ("Drum & Bass", "R&B & Soul"):
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
        assert chooser.chosen() == ("Alternative", "Rock")

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
        unmatched = grid("dance-house")
        assert silent.aside.text() != unmatched.aside.text()


class TestWhatItAnswers:
    def test_it_answers_as_a_line_edit_does(self, grid) -> None:
        """The panel holds it beside the lines and asks all of them `text()`."""
        chooser = grid()
        chooser.boxes["Punk"].setChecked(True)
        chooser.boxes["Rock"].setChecked(True)
        assert chooser.text() == "Punk; Rock"

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
        """The Green Day case: tagged Rock alone and plainly Punk as well."""
        chooser = grid("Rock")
        chooser.boxes["Punk"].setChecked(True)
        assert chooser.text() == "Punk; Rock"


def test_every_box_carries_the_house_ring(application: QApplication) -> None:
    """A checkbox is a stop on the keyboard ring, so it paints one.

    The structural suite forbids a plain QCheckBox anywhere in the package;
    this says the same thing about this grid in particular, in terms of what
    a listener would see rather than of what the source imports.
    """
    chooser = GenreGrid("")
    for name, box in chooser.boxes.items():
        assert isinstance(box, RingedCheckBox), name
