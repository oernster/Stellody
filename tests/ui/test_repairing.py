"""The screen that accepts a report's corrections, then takes them back.

Driven through the real dialog with a real QApplication, since what is being
checked is that pressing a control changes what the next load reports. The
scaffolding lives in repair_support beside this file.
"""

from __future__ import annotations

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMessageBox
from repair_support import COLLIDING, MemoryStore, buttons, exactly, labelled, opened

from stellody.application.repairs import AcceptedGroup, Repairs
from stellody.application.scan import LibraryView
from stellody.domain.album import Album
from stellody.domain.grouping import assemble_albums
from stellody.domain.health import IssueKind
from stellody.domain.overrides import Override, OverrideField
from stellody.ui.repairing import by_album, group_summary


@pytest.fixture
def repairs() -> Repairs:
    """A service over a store nobody has accepted anything in yet."""
    return Repairs(MemoryStore())


@pytest.fixture(autouse=True)
def never_really_ask(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """No test here may raise a real modal, which would hang the whole run.

    Answered No by default, so a test that reaches the confirmation without
    meaning to changes nothing and says so rather than stopping the suite. The
    one test that means to say yes overrides this.
    """
    asked: list[str] = []

    def answer(*args: object, **_kw: object) -> QMessageBox.StandardButton:
        asked.append(str(args[2]))
        return QMessageBox.StandardButton.No

    monkeypatch.setattr(QMessageBox, "question", answer)
    return asked


class TestWhatTheScreenOffers:
    def test_accept_everything_names_the_count_and_is_the_default(
        self, application, repairs
    ) -> None:
        """The default path, not a shortcut behind the per-issue flow."""
        dialog = opened(repairs, None)
        whole = labelled(dialog, "Accept everything")
        assert whole.isDefault()
        assert "(" in whole.text()
        dialog.deleteLater()

    def test_each_album_and_each_finding_can_be_accepted_on_its_own(
        self, application, repairs
    ) -> None:
        dialog = opened(repairs, None)
        texts = [button.text() for button in buttons(dialog)]
        assert any(text.startswith("Accept album") for text in texts)
        assert "Accept" in texts
        dialog.deleteLater()

    def test_nothing_is_accepted_when_it_opens(self, application, repairs) -> None:
        dialog = opened(repairs, None)
        assert repairs.accepted() == ()
        dialog.deleteLater()

    def test_the_scrolling_column_is_never_a_stop_on_the_ring(
        self, application, repairs
    ) -> None:
        """It holds real controls, so it has nothing of its own to offer."""
        dialog = opened(repairs, None)
        assert dialog._area.focusPolicy() is Qt.FocusPolicy.NoFocus
        assert dialog._area.viewport().focusPolicy() is Qt.FocusPolicy.NoFocus
        dialog.deleteLater()


class TestAccepting:
    def test_accepting_everything_empties_what_is_outstanding(
        self, application, repairs
    ) -> None:
        dialog = opened(repairs, None)
        labelled(dialog, "Accept everything").click()
        assert repairs.acceptable(dialog._view.issues) == ()
        dialog.deleteLater()

    def test_the_screen_redraws_to_say_what_is_now_true(
        self, application, repairs
    ) -> None:
        """The offer goes and the reset appears, without reopening anything."""
        dialog = opened(repairs, None)
        labelled(dialog, "Accept everything").click()
        texts = [button.text() for button in buttons(dialog)]
        assert not any(text.startswith("Accept everything") for text in texts)
        assert any(text.startswith("Reset everything") for text in texts)
        dialog.deleteLater()

    def test_accepting_one_finding_leaves_the_rest_outstanding(
        self, application, repairs
    ) -> None:
        dialog = opened(repairs, None)
        exactly(dialog, "Accept").click()
        assert repairs.accepted() != ()
        dialog.deleteLater()

    def test_what_is_accepted_is_grouped_with_a_reset_of_its_own(
        self, application, repairs
    ) -> None:
        dialog = opened(repairs, None)
        labelled(dialog, "Accept everything").click()
        assert any(button.text() == "Reset" for button in buttons(dialog))
        dialog.deleteLater()


class TestTakingItBack:
    def test_resetting_a_group_brings_its_finding_back(
        self, application, repairs
    ) -> None:
        """The raw tags were never altered, so there is nothing to restore."""
        dialog = opened(repairs, None)
        labelled(dialog, "Accept everything").click()
        assert repairs.acceptable(dialog._view.issues) == ()
        exactly(dialog, "Reset").click()
        assert repairs.acceptable(dialog._view.issues) != ()
        dialog.deleteLater()

    def test_resetting_everything_asks_first(
        self, application, repairs, never_really_ask
    ) -> None:
        """It undoes an unbounded amount of somebody's work in one press."""
        asked = never_really_ask
        dialog = opened(repairs, None)
        labelled(dialog, "Accept everything").click()
        before = repairs.accepted()
        labelled(dialog, "Reset everything").click()
        assert asked, "the reader must be asked before the lot goes"
        assert repairs.accepted() == before, "saying no must change nothing"
        dialog.deleteLater()

    def test_the_question_names_the_count(
        self, application, repairs, never_really_ask
    ) -> None:
        asked = never_really_ask
        dialog = opened(repairs, None)
        labelled(dialog, "Accept everything").click()
        labelled(dialog, "Reset everything").click()
        held = sum(group.count for group in repairs.accepted())
        assert str(held) in asked[0]
        dialog.deleteLater()

    def test_saying_yes_takes_the_lot_back(
        self, application, repairs, monkeypatch
    ) -> None:
        """The one test that answers yes, so it says so by overriding the guard."""
        monkeypatch.setattr(
            QMessageBox, "question", lambda *_a, **_k: QMessageBox.StandardButton.Yes
        )
        dialog = opened(repairs, None)
        labelled(dialog, "Accept everything").click()
        labelled(dialog, "Reset everything").click()
        assert repairs.accepted() == ()
        assert repairs.acceptable(dialog._view.issues) != ()
        dialog.deleteLater()


class TestTheWordsOnTheScreen:
    def test_findings_bucket_by_album_keeping_the_label(self) -> None:
        albums, issues = assemble_albums(COLLIDING)
        bucketed = by_album(issues)
        assert len(bucketed) == 1
        key, label, findings = bucketed[0]
        assert key == albums[0].identity.handle
        assert label == albums[0].identity.label
        assert findings

    def test_nothing_buckets_into_nothing(self) -> None:
        assert by_album(()) == ()

    @pytest.mark.parametrize(
        ("field", "words"),
        [
            (OverrideField.TRACK_NUMBER, "track numbers"),
            (OverrideField.DISC_NUMBER, "disc numbers"),
            (OverrideField.TITLE, "titles"),
            (OverrideField.ALBUM_ARTIST, "the album artist"),
        ],
    )
    def test_each_field_is_named_in_a_readers_words(
        self, field: OverrideField, words: str
    ) -> None:

        group = AcceptedGroup(
            album="handle",
            field=field,
            pins=(
                Override(
                    "handle",
                    field,
                    "x",
                    "" if field is OverrideField.ALBUM_ARTIST else "p",
                ),
            ),
        )
        assert words in group_summary(group, "An Album")

    def test_a_group_of_several_says_how_many(self) -> None:

        group = AcceptedGroup(
            album="handle",
            field=OverrideField.TITLE,
            pins=(
                Override("handle", OverrideField.TITLE, "a", "one"),
                Override("handle", OverrideField.TITLE, "b", "two"),
            ),
        )
        assert "2 files" in group_summary(group, "An Album")


def test_a_kind_that_proposes_nothing_is_never_offered(application, repairs) -> None:
    """Missing artwork has nothing to accept, so it is reported and left."""
    _, issues = assemble_albums(COLLIDING)
    assert all(
        issue.kind is not IssueKind.NO_ARTWORK for issue in repairs.acceptable(issues)
    )


def test_an_album_is_still_an_album(application) -> None:
    """Guards the fixture: these tests mean nothing if the album is empty."""
    albums, _ = assemble_albums(COLLIDING)
    assert isinstance(albums[0], Album)
    assert albums[0].tracks


class TestWhenTheControlsAreOffered:
    """A control that cannot act is disabled, as every other one here is."""

    def _window(self, repairs=None):
        from conftest import RecordingPlayer
        from tray_support import RememberingStore, build

        return build(RememberingStore(), RecordingPlayer(), repairs=repairs)

    def test_a_window_with_no_service_offers_no_repairs(self, application) -> None:
        made = self._window()
        made.take_issues(())
        assert not made.can_repair
        assert not made._bottom_tray.repair_button.isEnabled()
        made.close()

    def test_a_library_with_nothing_to_accept_offers_no_repairs(
        self, application, repairs
    ) -> None:
        """It would open a screen saying nothing, which is what disabled is for."""
        made = self._window(repairs)
        made.take_issues(())
        assert not made.can_repair
        assert not made._bottom_tray.repair_button.isEnabled()
        made.close()

    def test_findings_waiting_to_be_accepted_offer_repairs(
        self, application, repairs
    ) -> None:
        made = self._window(repairs)
        _, issues = assemble_albums(COLLIDING)
        made.take_issues(issues)
        assert made.can_repair
        assert made._bottom_tray.repair_button.isEnabled()
        made.close()

    def test_something_already_accepted_still_offers_repairs(
        self, application, repairs
    ) -> None:
        """So the lot can be taken back even once the report has emptied."""
        albums, issues = assemble_albums(COLLIDING)
        repairs.accept(LibraryView(albums=albums, issues=issues), issues)
        made = self._window(repairs)
        made.take_issues(())
        assert made.can_repair
        made.close()

    def test_the_health_dialogs_button_follows_the_same_answer(
        self, application, repairs
    ) -> None:
        """Two controls inches apart must not disagree about one question."""
        from stellody.ui.health import HealthDialog

        _, issues = assemble_albums(COLLIDING)
        offered = HealthDialog(issues, None, can_repair=True)
        withheld = HealthDialog(issues, None, can_repair=False)
        assert offered.repair_button.isEnabled()
        assert not withheld.repair_button.isEnabled()
        offered.deleteLater()
        withheld.deleteLater()
