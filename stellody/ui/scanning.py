"""Getting the library on screen: from the store on launch, from a scan on ask.

Split from the window because they answer different questions: over there is
what the window IS, here is how the library it shows arrives. Both routes end
the same way, with albums in the model and one line on the status bar.

Nothing here reaches for a control it was not given by the window it is mixed
into; the window owns the state and this owns the sequence.
"""

from __future__ import annotations

from PySide6.QtCore import Slot

from stellody.application.scan import LibraryView, ScanProgress, ScanReport
from stellody.domain.changes import compare_libraries
from stellody.ui.display import native_path
from stellody.ui.health import has_serious_issues
from stellody.ui.scan_summary import ScanSummaryDialog
from stellody.ui.settings_keys import (
    FALSE,
    SETTING_SCAN_FINISHED,
    STATUS_TIMEOUT_MS,
    TRUE,
)


class Scanning:
    """The library-loading half of the window."""

    @Slot()
    def rescan(self) -> None:
        """Scan the remembered folder again."""
        self.start_scan()

    def load_remembered(self) -> None:
        """Show the library the store already holds, reading no music at all.

        Launch does this instead of scanning. A scan reaches for the music
        folder, which may be a sleeping drive or a machine on the network;
        starting the application is not a request for one.
        """
        view = self._loader.run()
        self._issues = view.issues
        self.show_library(view.albums, view.art)
        self.statusBar().showMessage(self._remembered_message(view))

    def report_library_set_aside(self, moved) -> None:
        """Say that the library index would not open and what became of it.

        Said after the remembered library has been shown, so it is the last
        thing on the status line rather than the first thing overwritten.
        """
        self.statusBar().showMessage(
            f"The library index would not open, so it was set aside as "
            f"{moved.name}. Rescan to build a new one."
        )

    def _remembered_message(self, view: LibraryView) -> str:
        """What the status line says about a library nobody has just scanned."""
        if not self.library_root:
            return "Choose a music folder to begin."
        if self._flag(SETTING_SCAN_FINISHED, default=TRUE):
            return (
                f"{len(view.albums)} albums, {view.track_count} tracks. "
                "Rescan to pick up anything added since."
            )
        # A scan that was interrupted saved every folder it had reached, so
        # what is shown is real but short. Saying so beats letting the user
        # think their library has lost albums.
        return (
            f"{len(view.albums)} albums, {view.track_count} tracks. The last "
            "scan did not finish, so there may be more: choose Rescan."
        )

    def start_scan(self) -> bool:
        """Begin scanning the remembered folder; False when it cannot start."""
        root = self.library_root
        if not root:
            self.statusBar().showMessage(
                "Choose a music folder to begin.", STATUS_TIMEOUT_MS
            )
            return False
        if not self._runner.start(self._scan_session, root):
            return False
        self._set_rescan_enabled(False)
        # Recorded before the walk, so an interrupted scan is known for what it
        # is next time the application starts.
        self._settings.set_setting(SETTING_SCAN_FINISHED, FALSE)
        # Indeterminate again for the counting pass, which has no number yet.
        self._progress.setRange(0, 0)
        self._progress.setVisible(True)
        self.statusBar().showMessage(f"Scanning {native_path(root)}")
        return True

    @Slot(object)
    def _on_progress(self, progress: ScanProgress) -> None:
        """Say how far through the scan is, then which folder it is reading.

        The percentage leads, because a folder path is long enough to push it
        off the end of the line on a deep library.
        """
        if progress.total > 0:
            self._progress.setRange(0, progress.total)
            self._progress.setValue(progress.done)
        self.statusBar().showMessage(
            f"{progress.percent}% ({progress.done} of {progress.total}) "
            f"{native_path(progress.folder)}"
        )

    @Slot(object)
    def _on_completed(self, report: ScanReport) -> None:
        """Show the finished library, unless the scan was given up on."""
        self._progress.setVisible(False)
        self._set_rescan_enabled(True)
        if report.cancelled:
            # Everything it reached is saved; what it did not reach is unknown,
            # so the library on screen is left exactly as it was.
            self.statusBar().showMessage("Scan stopped.", STATUS_TIMEOUT_MS)
            return
        # Compared before the library on screen is replaced, since what is on
        # screen IS the reading this scan is being measured against. The runner
        # tears its thread down before it emits, so opening a dialog here has
        # nothing left waiting behind it.
        change = compare_libraries(self._all_albums, report.albums)
        self._settings.set_setting(SETTING_SCAN_FINISHED, TRUE)
        self._issues = report.issues
        self.show_library(report.albums, report.art)
        self.statusBar().showMessage(_summary(report), STATUS_TIMEOUT_MS)
        ScanSummaryDialog(change, report, self).exec()

    @Slot(str)
    def _on_failed(self, message: str) -> None:
        """Report a scan that could not finish."""
        self._progress.setVisible(False)
        self._set_rescan_enabled(True)
        self.statusBar().showMessage(f"Scan failed: {message}")

    def _set_rescan_enabled(self, enabled: bool) -> None:
        """Rescan is offered in two places, so both follow the same state.

        There is nothing to rescan while no music folder has been chosen, so
        that is part of the state rather than a refusal inside the errand.
        Without it a first run offers Rescan, which answers "Choose a music
        folder to begin" once it has been pressed. A control that cannot do its
        job says so before it is pressed here; that is what the ring on a
        disabled control is for.
        """
        offered = enabled and bool(self.library_root)
        self._rescan_action.setEnabled(offered)
        self._bottom_tray.rescan_button.setEnabled(offered)


def _summary(report: ScanReport) -> str:
    """The one-line result of a scan."""
    parts = [
        f"{len(report.albums)} albums",
        f"{report.track_count} tracks",
        f"{report.files_probed} files",
    ]
    if report.files_absent:
        parts.append(f"{report.files_absent} missing")
    if has_serious_issues(report.issues):
        parts.append(f"{len(report.issues)} issues, see Help then Library health")
    return "  |  ".join(parts)
