"""Taste profiles in the Discover dialog. `DISCOVERY.md` FR-D87 to FR-D94.

The two questions the profiles ask (a name to save under; a yes or no) are
answered by replacing the module's own functions, never by mocking Qt: what
is under test is what the dialog does with the answer.
"""

from __future__ import annotations

import pytest
from PySide6.QtWidgets import QApplication
from tray_support import RememberingStore

from stellody.domain.including import Including
from stellody.domain.release_years import ReleaseYears
from stellody.domain.taste import TasteProfile
from stellody.ui import taste_controls
from stellody.ui.discovery_dialog import DiscoveryDialog
from stellody.ui.settings_keys import SETTING_TASTE_PROFILES
from stellody.ui.taste_list import DELETE_TOOLTIP, NAME_COLUMN
from stellody.ui.taste_prompt import SaveTasteDialog
from stellody.ui.taste_store import TasteStore

JAZZ = ("Jazz", "Blues")
ELECTRONIC = ("Electronic",)
_JAZZ = (TasteProfile("Jazz", JAZZ),)


class Answers:
    """The answers the questions will get, in order; also what was asked."""

    def __init__(self, names=(), yeses=()) -> None:
        self.names = list(names)
        self.yeses = list(yeses)
        self.asked: list[str] = []
        self.offered: list[tuple[str, ...]] = []

    def name_for(self, _parent, genres):
        self.offered.append(genres)
        return self.names.pop(0) if self.names else None

    def said_yes(self, _parent, _title, text):
        self.asked.append(text)
        return self.yeses.pop(0) if self.yeses else False


@pytest.fixture
def answers(monkeypatch: pytest.MonkeyPatch) -> Answers:
    made = Answers()
    monkeypatch.setattr(taste_controls, "asked_name", made.name_for)
    monkeypatch.setattr(taste_controls, "said_yes", made.said_yes)
    return made


def _store(*profiles: TasteProfile) -> TasteStore:
    store = TasteStore(RememberingStore())
    store.keep(profiles)
    return store


def _dialog(store: TasteStore | None, started=None) -> DiscoveryDialog:
    start = (lambda *run: started.append(run)) if started is not None else None
    if start is None:
        return DiscoveryDialog(taste=store)
    return DiscoveryDialog(start=start, taste=store)


def _names(dialog: DiscoveryDialog) -> list[str]:
    return [name.text() for _, name in dialog.taste.list.rows]


def _choose(dialog: DiscoveryDialog, index: int) -> None:
    dialog.taste.list.rows[index][NAME_COLUMN].click()


class TestTheButton:
    def test_with_nothing_saved_it_is_disabled(self, application) -> None:
        """FR-D87: disabled, which wears the red ring."""
        assert not _dialog(_store()).taste.button.isEnabled()
        assert not _dialog(None).taste.button.isEnabled()

    def test_with_a_profile_saved_it_is_enabled_beside_select_all(
        self, application: QApplication
    ) -> None:
        dialog = _dialog(_store(TasteProfile("Jazz", JAZZ)))
        dialog.show()
        application.processEvents()
        button, select = dialog.taste.button, dialog.select_button
        assert button.isEnabled()
        assert select.geometry().right() < button.geometry().left()
        assert button.geometry().right() < dialog.find_button.geometry().left()
        assert int(button.focusPolicy()) != 0, "the keyboard reaches it"
        dialog.close()

    def test_it_lists_names_alphabetically_each_with_its_delete(
        self, application
    ) -> None:
        """FR-D88, FR-D92: Ambient, Jazz, rock, each row deleting its own."""
        dialog = _dialog(
            _store(
                TasteProfile("rock", ("Rock",)),
                TasteProfile("Ambient", ("Ambient",)),
                TasteProfile("Jazz", JAZZ),
            )
        )
        assert _names(dialog) == ["Ambient", "Jazz", "rock"]
        tips = [delete.toolTip() for delete, _ in dialog.taste.list.rows]
        assert tips == [
            DELETE_TOOLTIP.format(name=name) for name in ("Ambient", "Jazz", "rock")
        ]

    def test_the_delete_buttons_line_up_on_the_left(
        self, application: QApplication
    ) -> None:
        """Oliver's ruling: delete first in every row, so all share one column."""
        dialog = _dialog(
            _store(TasteProfile("A long profile name", JAZZ), TasteProfile("B", JAZZ))
        )
        dialog.show()
        dialog.taste.button.click()
        application.processEvents()
        rows = dialog.taste.list.rows
        lefts = {delete.mapToGlobal(delete.rect().topLeft()).x() for delete, _ in rows}
        assert len(lefts) == 1, "every delete button in one column"
        for delete, name in rows:
            assert delete.geometry().right() < name.geometry().left()
        dialog.taste.list.hide()
        dialog.close()

    def test_a_name_with_an_ampersand_keeps_it(self, application) -> None:
        dialog = _dialog(_store(TasteProfile("Rock & Roll", ("Rock",))))
        assert _names(dialog) == ["Rock && Roll"], "a single one would vanish"


class TestChoosing:
    def test_a_profile_puts_back_its_whole_selection(self, application) -> None:
        """FR-D89: genres, Include boxes and years (Oliver's ruling, 2026-10-12)."""
        profile = TasteProfile(
            "Jazz", JAZZ, Including(series=True, mixes=False), ReleaseYears(1990, 1999)
        )
        dialog = _dialog(_store(profile))
        dialog.grid.set_chosen(("Rock", "Electronic"))
        dialog.credits.setChecked(True)
        dialog.years.earliest.setText("2020")
        _choose(dialog, 0)
        assert set(dialog.chosen()) == set(JAZZ)
        assert dialog.including() == Including(series=True, mixes=False)
        assert dialog.years.earliest.text() == "1990"
        assert dialog.years.latest.text() == "1999"

    def test_a_genre_no_longer_offered_is_passed_over(self, application) -> None:
        dialog = _dialog(_store(TasteProfile("Old", ("Jazz", "Not a genre"))))
        _choose(dialog, 0)
        assert dialog.chosen() == ("Jazz",)


class TestSavingOnFind:
    def test_a_selection_already_saved_is_not_offered(self, application, answers):
        """FR-D90: the run starts with nothing asked."""
        started: list = []
        dialog = _dialog(_store(TasteProfile("Electronic", ELECTRONIC)), started)
        dialog.grid.set_chosen(ELECTRONIC)
        dialog.find_button.click()
        assert answers.offered == []
        assert len(started) == 1

    def test_a_new_selection_is_offered_and_not_now_saves_nothing(
        self, application, answers
    ):
        started: list = []
        store = _store(TasteProfile("Electronic", ELECTRONIC))
        dialog = _dialog(store, started)
        dialog.grid.set_chosen(("Electronic", "Jazz"))
        dialog.find_button.click()
        assert answers.offered == [dialog.chosen()]
        assert [p.name for p in store.profiles()] == ["Electronic"]
        assert len(started) == 1, "the run starts either way"

    def test_a_name_given_is_saved_and_the_run_starts(self, application, answers):
        answers.names = ["Late night"]
        started: list = []
        store = _store()
        dialog = _dialog(store, started)
        dialog.grid.set_chosen(JAZZ)
        dialog.find_button.click()
        assert store.profiles() == (TasteProfile("Late night", dialog.chosen()),)
        assert len(started) == 1

    def test_a_taken_name_is_replaced_once_confirmed(self, application, answers):
        """FR-D91: one profile named "jazz", holding the new genres."""
        answers.names, answers.yeses = ["jazz"], [True]
        store = _store(TasteProfile("Jazz", JAZZ))
        dialog = _dialog(store, [])
        dialog.grid.set_chosen(("Jazz", "Soul"))
        dialog.find_button.click()
        assert store.profiles() == (TasteProfile("jazz", dialog.chosen()),)
        assert "Jazz" in answers.asked[0]

    def test_refusing_to_replace_asks_for_a_name_again(self, application, answers):
        """Refused, the name field comes back; Not now then leaves Jazz alone."""
        answers.names, answers.yeses = ["jazz"], [False]
        store = _store(TasteProfile("Jazz", JAZZ))
        dialog = _dialog(store, [])
        dialog.grid.set_chosen(("Jazz", "Soul"))
        dialog.find_button.click()
        assert len(answers.offered) == 2
        assert store.profiles() == (TasteProfile("Jazz", JAZZ),)

    def test_with_nowhere_to_keep_them_nothing_is_offered(self, application, answers):
        dialog = _dialog(None, [])
        dialog.grid.set_chosen(JAZZ)
        dialog.find_button.click()
        assert answers.offered == []


class TestDeleting:
    def _delete(self, dialog: DiscoveryDialog, name: str) -> None:
        rows = dialog.taste.list.rows
        next(delete for delete, shown in rows if shown.text() == name).click()

    def test_a_profile_goes_only_once_confirmed(self, application, answers):
        """FR-D92: asked naming it; refused, both remain."""
        store = _store(
            TasteProfile("Ambient", ("Ambient",)), TasteProfile("Jazz", JAZZ)
        )
        dialog = _dialog(store)
        self._delete(dialog, "Jazz")
        assert "Jazz" in answers.asked[0]
        assert len(store.profiles()) == 2
        answers.yeses = [True]
        self._delete(dialog, "Jazz")
        assert [p.name for p in store.profiles()] == ["Ambient"]

    def test_deleting_the_last_disables_the_button(self, application, answers):
        answers.yeses = [True]
        store = _store(TasteProfile("Ambient", ("Ambient",)))
        dialog = _dialog(store)
        self._delete(dialog, "Ambient")
        assert store.profiles() == ()
        assert not dialog.taste.button.isEnabled()


class TestKeeping:
    def test_a_saved_profile_is_there_on_the_next_opening(self, application):
        """FR-D93."""
        store = _store(TasteProfile("Jazz", JAZZ))
        reopened = _dialog(TasteStore(store.settings))
        assert reopened.taste.button.isEnabled()
        assert _names(reopened)[0] == "Jazz"

    @pytest.mark.parametrize(
        "stored",
        [
            "not json",
            '{"name": "Jazz"}',
            '[{"name": "  "}, {"genres": ["Jazz"]}, {"name": "X", "genres": [1]}, 3]',
            '[{"name": "X", "genres": [], "years": {"earliest": 2, "latest": 1}}]',
            '[{"name": "X", "genres": [], "years": {"earliest": "1990"}}]',
            '[{"name": "X", "genres": [], "including": {"credits": 1}}]',
            '[{"name": "X", "genres": [], "including": [], "years": 5}]',
        ],
    )
    def test_a_setting_that_is_not_profiles_offers_none(self, application, stored):
        settings = RememberingStore({SETTING_TASTE_PROFILES: stored})
        dialog = _dialog(TasteStore(settings))
        assert not dialog.taste.button.isEnabled()

    def test_the_whole_selection_survives_the_round_trip(self, application):
        profile = TasteProfile(
            "Jazz", JAZZ, Including(credits=True), ReleaseYears(None, 1975)
        )
        assert _store(profile).profiles() == (profile,)

    def test_a_profile_kept_with_genres_alone_reads_with_the_defaults(
        self, application
    ):
        settings = RememberingStore(
            {SETTING_TASTE_PROFILES: '[{"name": "Jazz", "genres": ["Jazz"]}]'}
        )
        assert TasteStore(settings).profiles() == (TasteProfile("Jazz", ("Jazz",)),)

    def test_a_readable_profile_survives_beside_a_broken_one(self, application):
        settings = RememberingStore(
            {SETTING_TASTE_PROFILES: '[{"name": "Jazz", "genres": ["Jazz"]}, 7]'}
        )
        assert TasteStore(settings).profiles() == (TasteProfile("Jazz", ("Jazz",)),)


class TestTheOffer:
    def test_save_waits_for_a_name(self, application) -> None:
        """FR-D91: blank once trimmed is no name."""
        offer = SaveTasteDialog(JAZZ)
        assert not offer.save_button.isEnabled()
        offer.name.setText("   ")
        assert not offer.save_button.isEnabled()
        offer.accept()
        assert offer.chosen_name() is None
        offer.name.setText(" Late night ")
        assert offer.save_button.isEnabled()
        offer.save_button.click()
        assert offer.chosen_name() == "Late night"

    def test_not_now_gives_no_name(self, application) -> None:
        offer = SaveTasteDialog(JAZZ)
        offer.name.setText("Late night")
        offer.not_now_button.click()
        assert offer.chosen_name() is None
