"""Backing the library up and restoring it, from the File menu. BACKUP.md.

Split from the window for the reason the scanning and the leaving are: over
there is what the window IS, here is one errand a person can ask of it.

Every errand runs off the window's thread (FR-B13), says on the status line
which it is while it runs (FR-B35) and holds both commands back until it ends
(FR-B36), since a slow disk can make any of them take far longer than they do
on the machine they were measured on.

A confirmed restore ends with the window asking to be started again, then
quitting. The composition root reads that request once the claim to being the
running copy has been let go; a relaunch made before then would find this copy
still holding it and leave at once.
"""

from __future__ import annotations

import pathlib

from PySide6.QtCore import QStandardPaths, Slot
from PySide6.QtWidgets import QFileDialog, QMenu

from stellody.application.backing_up import Backups
from stellody.domain.backups import Manifest
from stellody.shared.version import APP_NAME
from stellody.ui import dialogs
from stellody.ui.display import native_path
from stellody.ui.errand_worker import ErrandRunner
from stellody.ui.menus import menu_action
from stellody.ui.settings_keys import SETTING_BACKUP_FOLDER

DOWNLOADS = QStandardPaths.StandardLocation.DownloadLocation
BACKUP_FILTER = "Backups (*.zip)"
# How a backup's moment is put to the person confirming a restore.
WRITTEN_FORMAT = "%d %B %Y at %H:%M"
RESTORE_TITLE = "Restore from backup"
MISSING_FOLDER_TITLE = "Music folder not found"


class KeepingBackups:
    """The backup half of the window."""

    def start_keeping_backups(self, backups: Backups | None) -> None:
        """Hold the errands; a window given none offers neither command."""
        self._backups = backups
        self._errands = ErrandRunner(self)
        self._restart_asked = False

    def _add_backup_actions(self, menu: QMenu) -> None:
        """Back up and Restore, directly below Rescan. FR-B01, FR-B19."""
        self._backup_action = menu_action(
            menu, self, "&Back up library...", self.back_up_library
        )
        self._restore_action = menu_action(
            menu, self, "Res&tore from backup...", self.restore_from_backup
        )
        self._offer_backups()

    @property
    def restart_asked(self) -> bool:
        """Whether a staged restore is waiting for this copy to start again."""
        return self._restart_asked

    def stop_backing_up(self) -> None:
        """Wait out an errand in flight, so nothing half written is left."""
        self._errands.wait()

    def _offer_backups(self) -> None:
        """Both commands, live only with a service and no errand running."""
        offered = self._backups is not None and not self._errands.running
        self._backup_action.setEnabled(offered)
        self._restore_action.setEnabled(offered)

    def _backup_folder(self) -> str:
        """The remembered folder while it is there; else Downloads. FR-B05 to B07."""
        remembered = self._settings.get_setting(SETTING_BACKUP_FOLDER, "")
        if remembered and pathlib.Path(remembered).is_dir():
            return remembered
        return QStandardPaths.writableLocation(DOWNLOADS)

    def _run(self, saying: str, errand, on_answer) -> None:
        """Start one errand, saying what it is, holding both commands back."""
        self._errands.start(errand, on_answer, self._errand_failed)
        self._offer_backups()
        self.statusBar().showMessage(saying)

    @Slot()
    def back_up_library(self) -> None:
        """Ask for a folder, then write a backup into it. FR-B02."""
        if self._backups is None or self._errands.running:
            return
        folder = QFileDialog.getExistingDirectory(
            self, "Choose where to keep the backup", self._backup_folder()
        )
        if not folder:
            return
        backups = self._backups
        self._run(
            f"Writing a backup to {native_path(folder)}...",
            lambda: backups.back_up(folder),
            lambda written: self._backed_up(folder, written),
        )

    def _backed_up(self, folder: str, written: object) -> None:
        """Remember the folder; say where the backup went. FR-B06, FR-B11."""
        self._offer_backups()
        self._settings.set_setting(SETTING_BACKUP_FOLDER, folder)
        self.statusBar().showMessage(f"Backed up to {native_path(str(written))}")

    def _errand_failed(self, error: Exception) -> None:
        """Say what stopped the errand, in the errand's own words. FR-B12."""
        self._offer_backups()
        self.statusBar().showMessage(str(error))

    @Slot()
    def restore_from_backup(self) -> None:
        """Ask for a backup, then check it before anything else. FR-B27."""
        if self._backups is None or self._errands.running:
            return
        chosen, _ = QFileDialog.getOpenFileName(
            self, "Choose a backup to restore", self._backup_folder(), BACKUP_FILTER
        )
        if not chosen:
            return
        backups = self._backups
        self._run(
            f"Checking {pathlib.Path(chosen).name}...",
            lambda: backups.verify(chosen),
            lambda manifest: self._checked(chosen, manifest),
        )

    def _checked(self, chosen: str, manifest: Manifest) -> None:
        """Ask before replacing anything; then save, stage and restart. FR-B22."""
        self._offer_backups()
        self.statusBar().clearMessage()
        safety_folder = self._backup_folder()
        question = (
            f"Restore the library from {pathlib.Path(chosen).name}, written "
            f"{manifest.written.strftime(WRITTEN_FORMAT)}?\n\n"
            "This replaces your current library, with its ratings, edits, "
            "settings and discovery results. A backup of them is saved first to "
            f"{native_path(safety_folder)}; {APP_NAME} then starts again."
        )
        if not dialogs.said_yes(self, RESTORE_TITLE, question):
            return
        backups = self._backups
        self._run(
            "Saving the current library before restoring...",
            lambda: backups.restore(chosen, safety_folder),
            self._staged,
        )

    def _staged(self, safety: object) -> None:
        """The restore waits for the next start; this copy leaves. FR-B23."""
        self._note(f"restore staged; safety backup {safety}; restarting")
        self._restart_asked = True
        self.quit_application()

    def report_restore(self, backup: str, safety: str, failure: str) -> None:
        """Say how the restore this start found went. FR-B32 to FR-B34."""
        name = pathlib.Path(backup).name
        kept = native_path(safety)
        if failure:
            self.statusBar().showMessage(
                f"The restore from {name} could not be completed ({failure}), so "
                f"the library was left as it was. The backup saved before it is {kept}."
            )
            return
        self.statusBar().showMessage(
            f"Restored from {name}. The library as it was before is saved as {kept}."
        )
        root = self.library_root
        if root and not pathlib.Path(root).is_dir():
            question = (
                f"The restored library's music folder, {native_path(root)}, is not "
                "on this computer. Choose a music folder now?"
            )
            if dialogs.said_yes(self, MISSING_FOLDER_TITLE, question):
                self.choose_folder()
