"""Taste profiles in the library's Filter by genre dialog. `DISCOVERY.md` FR-D96.

One list across both dialogs (Oliver's ruling, 2026-10-12): each dialog is
handed its own `TasteStore` over the SAME settings, as the window does, so what
is asserted is that the two meet in the setting rather than in a shared object.
"""

from __future__ import annotations

import pytest
from PySide6.QtWidgets import QDialog
from recording_player import RecordingPlayer
from tray_support import RememberingStore, build

from stellody.domain.taste import TasteProfile
from stellody.ui import taste_controls
from stellody.ui.discovery_dialog import DiscoveryDialog
from stellody.ui.filter_dialog import FilterDialog
from stellody.ui.taste_list import NAME_COLUMN
from stellody.ui.taste_store import TasteStore

JAZZ = TasteProfile("Jazz", ("Jazz", "Blues"))
AMBIENT = TasteProfile("Ambient", ("Ambient",))


def _settings(*profiles: TasteProfile) -> RememberingStore:
    settings = RememberingStore()
    TasteStore(settings).keep(profiles)
    return settings


def _filter(settings: RememberingStore) -> FilterDialog:
    return FilterDialog(taste=TasteStore(settings))


def _names(controls) -> list[str]:
    return [name.text() for _, name in controls.list.rows]


@pytest.fixture
def yes(monkeypatch: pytest.MonkeyPatch) -> None:
    """Every question answered yes."""
    monkeypatch.setattr(taste_controls, "said_yes", lambda *_asked: True)


def test_with_nothing_saved_the_button_is_disabled(application) -> None:
    assert not _filter(_settings()).taste.button.isEnabled()
    assert not FilterDialog().taste.button.isEnabled(), "nowhere to keep them"


def test_choosing_a_profile_ticks_exactly_its_genres(application) -> None:
    """The box apart from the catalogue is no genre, so it is left alone."""
    dialog = _filter(_settings(JAZZ))
    dialog.grid.set_chosen(("Rock",))
    dialog.unstated_box.setChecked(True)
    dialog.taste.list.rows[0][NAME_COLUMN].click()
    assert set(dialog.grid.chosen()) == set(JAZZ.genres)
    assert dialog.unstated_box.isChecked()
    assert dialog.show_button.isEnabled()


def test_a_profile_saved_from_discover_is_offered_here(
    application, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Saved the way a person saves one: Find, then a name given."""
    monkeypatch.setattr(taste_controls, "asked_name", lambda *_asked: "Late night")
    settings = _settings()
    discover = DiscoveryDialog(start=lambda *_run: None, taste=TasteStore(settings))
    discover.grid.set_chosen(JAZZ.genres)
    discover.find_button.click()
    dialog = _filter(settings)
    assert _names(dialog.taste) == ["Late night"]
    dialog.taste.list.rows[0][NAME_COLUMN].click()
    assert set(dialog.grid.chosen()) == set(JAZZ.genres)


def test_the_window_opens_its_filter_on_its_own_profiles(
    application, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The wiring: the filter the window opens reads the window's settings."""
    offered: list[list[str]] = []

    def looked(dialog: FilterDialog) -> int:
        offered.append(_names(dialog.taste))
        return QDialog.DialogCode.Rejected

    monkeypatch.setattr(FilterDialog, "exec", looked)
    window = build(_settings(JAZZ), RecordingPlayer())
    window.open_filter()
    window.close()
    assert offered == [["Jazz"]]


def test_a_profile_deleted_here_is_gone_from_discover(application, yes) -> None:
    settings = _settings(AMBIENT, JAZZ)
    dialog = _filter(settings)
    dialog.taste.list.rows[1][0].click()
    assert _names(dialog.taste) == ["Ambient"]
    discover = DiscoveryDialog(taste=TasteStore(settings))
    assert _names(discover.taste) == ["Ambient"]
