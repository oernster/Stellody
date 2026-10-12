"""Back up and Restore on the File menu. BACKUP.md.

FR-B01 to FR-B13, FR-B19 to FR-B23, FR-B35 and FR-B36.
"""

from __future__ import annotations

import threading

import pytest
from backup_doubles import HeldArchive, built, file_menu_labels, settled
from PySide6.QtCore import QStandardPaths
from PySide6.QtWidgets import QApplication, QFileDialog
from tray_support import RememberingStore

from stellody.ui import dialogs
from stellody.ui.display import native_path
from stellody.ui.settings_keys import SETTING_BACKUP_FOLDER

DOWNLOADS = QStandardPaths.writableLocation(
    QStandardPaths.StandardLocation.DownloadLocation
)


@pytest.fixture
def rig(application: QApplication):
    """A window over a held archive and a store that remembers."""
    archive = HeldArchive()
    store = RememberingStore()
    left: list[int] = []
    window = built(archive, store, left)
    yield window, archive, store, left
    archive.release.set()
    window._quitting = True
    window.close()
    window.deleteLater()


def _picking(monkeypatch, answer: str) -> list[str]:
    """Stand the folder picker in; record where it opened."""
    opened: list[str] = []

    def picked(parent, title, start):
        opened.append(start)
        return answer

    monkeypatch.setattr(QFileDialog, "getExistingDirectory", picked)
    return opened


def _choosing(monkeypatch, answer: str) -> list[str]:
    """Stand the file picker in; record where it opened."""
    opened: list[str] = []

    def chosen(parent, title, start, wanted):
        opened.append(start)
        return answer, wanted

    monkeypatch.setattr(QFileDialog, "getOpenFileName", chosen)
    return opened


def _answering(monkeypatch, answer: bool) -> list[str]:
    """Stand the confirmation in; record what it asked."""
    asked: list[str] = []

    def said(parent, title, text):
        asked.append(text)
        return answer

    monkeypatch.setattr(dialogs, "said_yes", said)
    return asked


def test_back_up_sits_below_rescan(rig) -> None:
    """FR-B01."""
    labels = file_menu_labels(rig[0])
    assert labels[labels.index("&Rescan") + 1] == "&Back up library..."


def test_restore_sits_below_back_up(rig) -> None:
    """FR-B19."""
    labels = file_menu_labels(rig[0])
    assert labels[labels.index("&Back up library...") + 1] == "Res&tore from backup..."


def test_a_window_without_the_errands_offers_neither(application) -> None:
    window = built(None, RememberingStore(), [])
    assert not window._backup_action.isEnabled()
    assert not window._restore_action.isEnabled()
    window.back_up_library()
    window.restore_from_backup()
    window._quitting = True
    window.close()
    window.deleteLater()


def test_cancelling_the_folder_writes_nothing(rig, monkeypatch) -> None:
    """FR-B02."""
    window, archive, _, _ = rig
    _picking(monkeypatch, "")
    window.back_up_library()
    assert not window._errands.running and archive.threads == []


def test_the_first_backup_opens_on_downloads(rig, monkeypatch) -> None:
    """FR-B05."""
    opened = _picking(monkeypatch, "")
    rig[0].back_up_library()
    assert opened == [DOWNLOADS]


def test_the_next_backup_opens_where_the_last_went(rig, monkeypatch, tmp_path) -> None:
    """FR-B06."""
    window, _, store, _ = rig
    _picking(monkeypatch, str(tmp_path))
    window.back_up_library()
    settled(window)
    assert store.get_setting(SETTING_BACKUP_FOLDER) == str(tmp_path)
    opened = _picking(monkeypatch, "")
    window.back_up_library()
    assert opened == [str(tmp_path)]


def test_a_vanished_folder_falls_back_to_downloads(rig, monkeypatch, tmp_path) -> None:
    """FR-B07."""
    window, _, store, _ = rig
    store.set_setting(SETTING_BACKUP_FOLDER, str(tmp_path / "gone"))
    opened = _picking(monkeypatch, "")
    window.back_up_library()
    assert opened == [DOWNLOADS]


def test_a_finished_backup_names_its_file(rig, monkeypatch, tmp_path) -> None:
    """FR-B11."""
    window = rig[0]
    _picking(monkeypatch, str(tmp_path))
    window.back_up_library()
    settled(window)
    written = f"{tmp_path}/app-backup-2026-10-12-1405.zip"
    assert window.statusBar().currentMessage() == f"Backed up to {native_path(written)}"


def test_a_failed_backup_says_why(rig, monkeypatch, tmp_path) -> None:
    """FR-B12: the errand's own words, naming the folder."""
    window, archive, _, _ = rig
    archive.fail = f"The backup could not be written to {tmp_path}: full"
    _picking(monkeypatch, str(tmp_path))
    window.back_up_library()
    settled(window)
    assert window.statusBar().currentMessage() == archive.fail
    assert window._backup_action.isEnabled()


def test_the_backup_runs_off_the_window_thread(rig, monkeypatch, tmp_path) -> None:
    """FR-B13."""
    window, archive, _, _ = rig
    _picking(monkeypatch, str(tmp_path))
    window.back_up_library()
    settled(window)
    assert archive.threads and archive.threads[0] != threading.get_ident()


def test_a_running_backup_is_shown(rig, monkeypatch, tmp_path) -> None:
    """FR-B35."""
    window, archive, _, _ = rig
    archive.release.clear()
    _picking(monkeypatch, str(tmp_path))
    window.back_up_library()
    said = window.statusBar().currentMessage()
    assert said == f"Writing a backup to {native_path(str(tmp_path))}..."
    archive.release.set()
    settled(window)


def test_both_commands_wait_for_the_running_one(rig, monkeypatch, tmp_path) -> None:
    """FR-B36: held back while it runs; asked again, nothing new starts."""
    window, archive, _, _ = rig
    archive.release.clear()
    _picking(monkeypatch, str(tmp_path))
    window.back_up_library()
    assert not window._backup_action.isEnabled()
    assert not window._restore_action.isEnabled()
    window.back_up_library()
    window.restore_from_backup()
    archive.release.set()
    settled(window)
    assert len(archive.threads) == 1
    assert window._backup_action.isEnabled() and window._restore_action.isEnabled()


def test_cancelling_the_backup_choice_restores_nothing(rig, monkeypatch) -> None:
    window = rig[0]
    _choosing(monkeypatch, "")
    window.restore_from_backup()
    assert not window._errands.running


def test_a_refused_backup_is_said(rig, monkeypatch) -> None:
    """FR-B28: no confirmation, the refusal on the status line."""
    window, archive, _, _ = rig
    archive.refuse = True
    _choosing(monkeypatch, "C:/x.zip")
    asked = _answering(monkeypatch, True)
    window.restore_from_backup()
    settled(window)
    assert asked == []
    assert window.statusBar().currentMessage() == "x.zip cannot be restored: torn."


def test_cancelling_the_restore_changes_nothing(rig, monkeypatch) -> None:
    """FR-B22: the question names the file and the date it was written."""
    window, archive, _, left = rig
    _choosing(monkeypatch, "C:/x.zip")
    asked = _answering(monkeypatch, False)
    window.restore_from_backup()
    settled(window)
    assert "x.zip, written 12 October 2026 at 14:05" in asked[0]
    assert archive.staged == [] and not window.restart_asked and left == []


def test_a_confirmed_restore_stages_then_starts_again(rig, monkeypatch) -> None:
    """FR-B20, FR-B23: the safety backup goes to Downloads, then the window leaves."""
    window, archive, _, left = rig
    _choosing(monkeypatch, "C:/x.zip")
    _answering(monkeypatch, True)
    window.restore_from_backup()
    settled(window)
    settled(window)
    safety = f"{DOWNLOADS}/app-before-restore-2026-10-12-1405.zip"
    assert archive.staged == [("C:/x.zip", safety)]
    assert window.restart_asked and left == [1]
