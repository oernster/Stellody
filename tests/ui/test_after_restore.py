"""What the start after a restore says. BACKUP.md FR-B32 to FR-B34."""

from __future__ import annotations

import pytest
from backup_doubles import HeldArchive, built
from PySide6.QtWidgets import QApplication
from tray_support import RememberingStore

from stellody.ui import dialogs
from stellody.ui.display import native_path
from stellody.ui.settings_keys import SETTING_ROOT


@pytest.fixture
def rig(application: QApplication):
    """A window over a store that remembers, with its folder chooser watched."""
    store = RememberingStore()
    window = built(HeldArchive(), store, [])
    chosen: list[int] = []
    window.choose_folder = lambda: chosen.append(1)
    yield window, store, chosen
    window._quitting = True
    window.close()
    window.deleteLater()


def _answering(monkeypatch, answer: bool) -> list[str]:
    asked: list[str] = []

    def said(parent, title, text):
        asked.append(text)
        return answer

    monkeypatch.setattr(dialogs, "said_yes", said)
    return asked


def test_the_restore_is_reported(rig, monkeypatch, tmp_path) -> None:
    """FR-B33: names both zips."""
    window, store, _ = rig
    store.set_setting(SETTING_ROOT, str(tmp_path))
    asked = _answering(monkeypatch, True)
    window.report_restore("D:/b/app-backup.zip", "D:/b/app-before.zip", "")
    said = window.statusBar().currentMessage()
    assert said == (
        "Restored from app-backup.zip. The library as it was before is saved as "
        f"{native_path('D:/b/app-before.zip')}."
    )
    assert asked == [], "a folder that is there needs no question"


def test_a_missing_folder_is_named(rig, monkeypatch, tmp_path) -> None:
    """FR-B32: named, with a music folder offered; yes opens the chooser."""
    window, store, chosen = rig
    store.set_setting(SETTING_ROOT, str(tmp_path / "Music"))
    asked = _answering(monkeypatch, True)
    window.report_restore("D:/b/app-backup.zip", "D:/b/app-before.zip", "")
    assert native_path(str(tmp_path / "Music")) in asked[0]
    assert chosen == [1]


def test_declining_leaves_the_folder_alone(rig, monkeypatch, tmp_path) -> None:
    window, store, chosen = rig
    store.set_setting(SETTING_ROOT, str(tmp_path / "Music"))
    _answering(monkeypatch, False)
    window.report_restore("D:/b/app-backup.zip", "D:/b/app-before.zip", "")
    assert chosen == []


def test_a_library_with_no_folder_asks_nothing(rig, monkeypatch) -> None:
    window, _, chosen = rig
    asked = _answering(monkeypatch, True)
    window.report_restore("D:/b/app-backup.zip", "D:/b/app-before.zip", "")
    assert asked == [] and chosen == []


def test_a_failure_part_way_is_said(rig, monkeypatch) -> None:
    """FR-B34: the reason, that nothing changed and where the safety backup is."""
    window, _, _ = rig
    asked = _answering(monkeypatch, True)
    window.report_restore("D:/b/app-backup.zip", "D:/b/app-before.zip", "disk full")
    said = window.statusBar().currentMessage()
    assert "app-backup.zip could not be completed (disk full)" in said
    assert "left as it was" in said and native_path("D:/b/app-before.zip") in said
    assert asked == []
