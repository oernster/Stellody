"""FR-D99: both genre choosers ask for years, as Discover does.

The library's Filter by genre and the answer's Filter the answer each carry
the two year fields below the genres. What they narrow to is the domain's rule
(`tests/domain/test_filtering_by_year.py`); this is where the fields, the
refusal, Clear, the taste profiles and the answer's top line are read off the
screen.
"""

from __future__ import annotations

import pytest
from PySide6.QtWidgets import QDialog
from tray_support import RememberingStore, track

from stellody.domain.album import Album
from stellody.domain.discovery import Gaps, ReleaseGroup
from stellody.domain.identity import AlbumIdentity
from stellody.domain.narrowing import Narrowing
from stellody.domain.release_years import ANY_YEAR, ReleaseYears
from stellody.domain.showing import EVERYTHING
from stellody.domain.taste import TasteProfile
from stellody.ui import taste_controls
from stellody.ui.filter_dialog import FilterDialog
from stellody.ui.filtering import worded
from stellody.ui.palette import Mode
from stellody.ui.results_dialog import ResultsDialog
from stellody.ui.results_filter import ResultsFilterDialog
from stellody.ui.results_words import withheld
from stellody.ui.taste_list import NAME_COLUMN
from stellody.ui.taste_store import TasteStore
from stellody.ui.year_fields import ANY_YEAR_HINT

THIS_YEAR = 2026
EIGHTIES = ReleaseYears(1980, 1989)
EIGHTIES_JAZZ = TasteProfile("Eighties jazz", ("Jazz",), years=EIGHTIES)


def _settings(*profiles: TasteProfile) -> RememberingStore:
    settings = RememberingStore()
    TasteStore(settings).keep(profiles)
    return settings


def _library_filter(
    settings: RememberingStore | None = None, asked: Narrowing | None = None
) -> FilterDialog:
    taste = None if settings is None else TasteStore(settings)
    return FilterDialog(asked, taste=taste, year_now=THIS_YEAR)


def _answer_filter(
    settings: RememberingStore | None = None, years: ReleaseYears = ANY_YEAR
) -> ResultsFilterDialog:
    taste = None if settings is None else TasteStore(settings)
    return ResultsFilterDialog(
        ("Jazz", "Rock"), taste=taste, years=years, year_now=THIS_YEAR
    )


def _type(chooser, earliest: str, latest: str) -> None:
    chooser.years.fields.earliest.setText(earliest)
    chooser.years.fields.latest.setText(latest)


def _apply(chooser):
    if isinstance(chooser, FilterDialog):
        return chooser.show_button
    return chooser.filter_button


@pytest.fixture(params=["library", "answer"])
def chooser(request, application):
    """Each genre chooser in turn, opened on no filter."""
    if request.param == "library":
        return _library_filter()
    return _answer_filter()


class TestTheFields:
    def test_they_open_empty_saying_any_year(self, chooser) -> None:
        fields = chooser.years.fields
        assert (fields.earliest.text(), fields.latest.text()) == ("", "")
        assert fields.earliest.placeholderText() == ANY_YEAR_HINT
        assert chooser.years.refusal.isHidden()

    def test_years_alone_are_enough_to_filter_by(self, chooser) -> None:
        assert not _apply(chooser).isEnabled()
        _type(chooser, "1980", "1989")
        assert _apply(chooser).isEnabled()
        assert chooser.years.years() == EIGHTIES

    def test_clear_empties_them(self, chooser) -> None:
        _type(chooser, "1980", "1989")
        chooser.clear()
        assert chooser.years.years() == ANY_YEAR

    def test_they_open_holding_the_years_already_asked(self, application) -> None:
        """A filter is adjusted rather than rebuilt, years and all."""
        library = _library_filter(asked=Narrowing(years=EIGHTIES))
        answer = _answer_filter(years=EIGHTIES)
        for opened in (library, answer):
            assert opened.years.years() == EIGHTIES
            assert _apply(opened).isEnabled()


class TestRefusing:
    """FR-D59 as Discover has it: said, never corrected."""

    def test_years_that_cannot_be_used_are_said_and_take_the_press_away(
        self, chooser
    ) -> None:
        chooser.grid.set_chosen(("Jazz",))
        _type(chooser, "1990", "1980")
        assert not chooser.years.refusal.isHidden()
        assert "later than the to year" in chooser.years.refusal.text()
        assert not _apply(chooser).isEnabled()

    def test_the_press_is_guarded_from_the_keyboard_too(self, chooser) -> None:
        chooser.grid.set_chosen(("Jazz",))
        _type(chooser, "198", "")
        chooser.accept()
        assert chooser.result() != QDialog.DialogCode.Accepted


@pytest.fixture
def named_late_night(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, ...]]:
    """Every offer answered with a name; the genres each was made over."""
    asked: list[tuple[str, ...]] = []

    def name_for(_parent, genres: tuple[str, ...]) -> str:
        asked.append(genres)
        return "Late night"

    monkeypatch.setattr(taste_controls, "asked_name", name_for)
    return asked


class TestTasteProfiles:
    def test_choosing_a_profile_puts_its_years_back(self, application) -> None:
        for opened in (
            _library_filter(_settings(EIGHTIES_JAZZ)),
            _answer_filter(_settings(EIGHTIES_JAZZ)),
        ):
            _type(opened, "2000", "")
            opened.taste.list.rows[0][NAME_COLUMN].click()
            assert opened.years.years() == EIGHTIES

    def test_a_filter_saves_its_years_with_its_genres(
        self, application, named_late_night
    ) -> None:
        for opened in ("library", "answer"):
            settings = _settings()
            dialog = (
                _library_filter(settings)
                if opened == "library"
                else _answer_filter(settings)
            )
            dialog.grid.set_chosen(("Jazz",))
            _type(dialog, "1980", "1989")
            _apply(dialog).click()
            saved = TasteStore(settings).profiles()
            assert saved == (TasteProfile("Late night", ("Jazz",), years=EIGHTIES),)

    def test_the_same_genres_over_other_years_are_offered(
        self, application, named_late_night
    ) -> None:
        dialog = _library_filter(_settings(EIGHTIES_JAZZ))
        dialog.grid.set_chosen(("Jazz",))
        _apply(dialog).click()
        assert named_late_night == [("Jazz",)]

    def test_the_same_genres_and_years_are_not_offered_again(
        self, application, named_late_night
    ) -> None:
        dialog = _answer_filter(_settings(EIGHTIES_JAZZ))
        dialog.grid.set_chosen(("Jazz",))
        _type(dialog, "1980", "1989")
        _apply(dialog).click()
        assert named_late_night == []


class TestTheLibraryButton:
    def test_the_tooltip_names_the_years(self) -> None:
        asked = Narrowing(wanted=("Rock",), years=EIGHTIES)
        assert worded(asked) == "Rock; albums released 1980 to 1989"
        assert worded(Narrowing(years=ReleaseYears(1980, None))) == (
            "albums released 1980 or later"
        )


def _album(artist: str) -> Album:
    return Album(
        identity=AlbumIdentity(album_artist=artist, title=f"{artist} Album"),
        tracks=(track(1),),
        genre="Rock",
    )


ANSWER = (
    Gaps("AC/DC", albums=(ReleaseGroup(title="Flick of the Switch", released="1983"),)),
    Gaps("Airbourne", albums=(ReleaseGroup(title="Boneshaker", released="2019"),)),
)


class TestTheAnswer:
    def _dialog(self) -> ResultsDialog:
        return ResultsDialog(
            ANSWER,
            mode=Mode.DARK,
            ticked=("Rock",),
            library=(_album("AC/DC"), _album("Airbourne")),
            remembered={},
        )

    def test_only_albums_released_in_the_years_are_dealt(self, application) -> None:
        dialog = self._dialog()
        dialog.filter_to((), EVERYTHING, EIGHTIES)
        assert len(dialog.sources) == 1
        assert dialog.sources[0].text(0).startswith("AC/DC")
        assert dialog.filter_button.isChecked()
        dialog.filter_to((), EVERYTHING, ANY_YEAR)
        assert len(dialog.sources) == len(ANSWER)
        assert not dialog.filter_button.isChecked()

    def test_the_line_says_the_years(self, application) -> None:
        dialog = self._dialog()
        dialog.filter_to(("Rock",), EVERYTHING, EIGHTIES)
        assert dialog.top.withheld.text() == withheld(("Rock",), 0, EIGHTIES)
        assert dialog.top.withheld.text() == (
            "Filtered to Rock; albums released 1980 to 1989"
        )

    def test_the_chooser_opens_on_the_years_in_use(self, application) -> None:
        dialog = self._dialog()
        dialog.filter_to((), EVERYTHING, EIGHTIES)
        assert dialog.filter_dialog().years.years() == EIGHTIES
