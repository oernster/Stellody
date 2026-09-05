"""Asking the library for a genre, then what the grid holds.

Three halves, since the feature is three pieces: the dialog collects the
question, the window holds it and composes it with the search, the button
says whether anything is being asked for at all.
"""

from __future__ import annotations

import pytest
from conftest import RecordingPlayer
from PySide6.QtWidgets import QApplication, QDialog
from tray_support import RememberingStore, build, track

from stellody.application.artwork import AlbumArtSources
from stellody.domain.album import Album
from stellody.domain.identity import AlbumIdentity
from stellody.domain.narrowing import Narrowing
from stellody.ui.filter_dialog import FilterDialog
from stellody.ui.filtering import UNSTATED_WORD, worded
from stellody.ui.row_text import Column
from stellody.ui.theme import Mode, stylesheet
from stellody.ui.toolbar import FILTER_TOOLTIP


def _album(title: str, genre: str) -> Album:
    """One album stated with that genre, whatever the genre is."""
    return Album(
        identity=AlbumIdentity(album_artist="Holst", title=title),
        tracks=(track(1), track(2)),
        genre=genre,
    )


ROCK = _album("Awesome", "Rock")
TRANCE = _album("Ambient", "Trance; Electronic")
UNTAGGED = _album("Untagged", "")
LIBRARY = (ROCK, TRANCE, UNTAGGED)
ART = tuple(
    AlbumArtSources(key=album.identity.art_key, sidecars=()) for album in LIBRARY
)


@pytest.fixture
def window(application: QApplication):
    """A real window holding three albums, one of each interesting kind."""
    made = build(RememberingStore(), RecordingPlayer())
    made.show_library(LIBRARY, ART)
    application.processEvents()
    yield made
    made.close()


def shown(window) -> list[str]:
    """The album titles the library is showing, top to bottom."""
    model = window._model
    return [
        model.data(model.index(row, Column.TITLE, model.index(-1, 0)))
        for row in range(model.rowCount(model.index(-1, 0)))
    ]


class TestTheDialog:
    def test_it_opens_holding_what_is_already_asked_for(self, application) -> None:
        dialog = FilterDialog(Narrowing(wanted=("Rock",), unstated=True))
        assert dialog.grid.boxes["Rock"].isChecked()
        assert dialog.unstated_box.isChecked()

    def test_ticking_a_style_leaves_its_main_alone(self, application) -> None:
        """A tick is a question here. Ticking Trance is not asking for every
        kind of electronic music, which is what stating Trance would mean."""
        dialog = FilterDialog()
        dialog.grid.boxes["Trance"].setChecked(True)
        assert not dialog.grid.boxes["Electronic"].isChecked()
        assert dialog.narrowing().wanted == ("Trance",)

    def test_it_says_nothing_about_an_album_it_has_none_of(self, application) -> None:
        """The line under the boxes belongs to describing one album."""
        assert FilterDialog().grid.aside.text() == ""

    def test_clearing_unticks_everything_without_closing(self, application) -> None:
        dialog = FilterDialog(Narrowing(wanted=("Rock",), unstated=True))
        dialog.clear()
        assert dialog.narrowing().is_open
        assert dialog.isVisible() is False, "clearing is not an answer"

    def test_what_it_answers_with(self, application) -> None:
        dialog = FilterDialog()
        dialog.grid.boxes["Rock"].setChecked(True)
        dialog.unstated_box.setChecked(True)
        asked = dialog.narrowing()
        assert asked.wanted == ("Rock",)
        assert asked.unstated


class TestTheLibraryIsNarrowed:
    def _ask(self, window, asked: Narrowing) -> None:
        """Answer the dialog with that question, as pressing Show does."""
        window._narrowing = asked
        window.show_filtering()
        window._narrow()

    def test_everything_is_shown_to_start_with(self, window) -> None:
        assert shown(window) == ["Ambient", "Awesome", "Untagged"]

    def test_one_genre_leaves_the_albums_stated_with_it(self, window) -> None:
        self._ask(window, Narrowing(wanted=("Rock",)))
        assert shown(window) == ["Awesome"]

    def test_two_genres_leave_the_union_of_both(self, window) -> None:
        self._ask(window, Narrowing(wanted=("Rock", "Trance")))
        assert shown(window) == ["Ambient", "Awesome"]

    def test_not_stated_reaches_the_albums_no_tick_can(self, window) -> None:
        self._ask(window, Narrowing(unstated=True))
        assert shown(window) == ["Untagged"]

    def test_clearing_it_restores_the_whole_library(self, window) -> None:
        self._ask(window, Narrowing(wanted=("Rock",)))
        self._ask(window, Narrowing())
        assert shown(window) == ["Ambient", "Awesome", "Untagged"]

    def test_a_phrase_searches_what_the_filter_left(self, window) -> None:
        """Rather than the library behind it, which would put back an album
        the filter had just taken away."""
        self._ask(window, Narrowing(wanted=("Rock",)))
        window.search_changed("Ambient")
        assert shown(window) == []

    def test_the_filter_survives_the_phrase_being_cleared(self, window) -> None:
        self._ask(window, Narrowing(wanted=("Rock",)))
        window.search_changed("Awesome")
        window.search_changed("")
        assert shown(window) == ["Awesome"]


class TestTheButtonSaysWhetherAnythingIsAsked:
    def test_it_is_up_while_the_whole_library_is_showing(self, window) -> None:
        assert not window._tray.filter_button.isChecked()
        assert window._tray.filter_button.toolTip() == FILTER_TOOLTIP

    def test_it_goes_down_and_names_what_is_asked_for(self, window) -> None:
        window._narrowing = Narrowing(wanted=("Rock", "Trance"))
        window.show_filtering()
        assert window._tray.filter_button.isChecked()
        assert window._tray.filter_button.toolTip() == "Showing Rock, Trance"

    def test_it_looks_different_while_it_is_on(self, application, window) -> None:
        """A tooltip is read by somebody already asking; the fill is read by
        somebody wondering why the library looks short."""
        application.setStyleSheet(stylesheet(Mode.DARK))
        application.processEvents()
        button = window._tray.filter_button
        up = button.grab().toImage()
        window._narrowing = Narrowing(wanted=("Rock",))
        window.show_filtering()
        application.processEvents()
        assert button.grab().toImage() != up, "nothing on screen says it is on"

    def test_the_box_apart_from_the_catalogue_is_named_in_words(self) -> None:
        assert worded(Narrowing(unstated=True)) == UNSTATED_WORD
        assert worded(Narrowing(wanted=("Rock",), unstated=True)) == (
            f"Rock, {UNSTATED_WORD}"
        )


class TestOpeningIt:
    def test_cancelling_leaves_the_library_as_it_was(self, window, monkeypatch) -> None:
        monkeypatch.setattr(FilterDialog, "exec", lambda self: QDialog.Rejected)
        window._narrowing = Narrowing(wanted=("Rock",))
        window.open_filter()
        assert window._narrowing == Narrowing(wanted=("Rock",))
        assert shown(window) == ["Ambient", "Awesome", "Untagged"]

    def test_showing_narrows_to_what_was_ticked(self, window, monkeypatch) -> None:
        def tick_rock(dialog) -> int:
            dialog.grid.boxes["Rock"].setChecked(True)
            return QDialog.Accepted

        monkeypatch.setattr(FilterDialog, "exec", tick_rock)
        window.open_filter()
        assert window._narrowing.wanted == ("Rock",)
        assert shown(window) == ["Awesome"]
        assert window._tray.filter_button.isChecked()
