"""The discovery half of the window: opening the dialog and driving a run.

The window owns the dialog and the thread; the dialog owns neither. That is
what lets the dialog be driven with nothing behind it; it is also why this is
a separate concern rather than more of `main_window`.

**Writing the answer is handed in rather than reached for.** The UI layer is a
client of the application layer and of nothing else, so where a file goes is
somebody else's decision arriving as a callable.

**Every ending says which ending it was.** A run that found nothing, one nobody
could reach, one somebody stopped and one whose file would not write are four
different things, so a listener is owed which of them happened rather than a
dialog that simply stops moving.
"""

from __future__ import annotations

from collections.abc import Callable

from stellody.application.discovering import Discovery
from stellody.application.values import DiscoveryProgress, RunOutcome, RunReport
from stellody.ui.discovery_dialog import DiscoveryDialog
from stellody.ui.discovery_worker import DiscoveryRunner
from stellody.ui.tray_metrics import DISCOVER_TOOLTIP, STOP_DISCOVERY_TOOLTIP

# Handed a finished run; answers where it was written. Raises where it could
# not be, which is reported rather than swallowed.
WriteDiscovery = Callable[[RunReport], object]

FOUND = (
    "Found {albums} albums and {artists} artists you do not hold. Written to {where}"
)
FOUND_NOTHING = "Nothing missing was found in those genres."
NOTHING_TO_ASK = (
    "Nothing in the library carries those genres, so there was nobody to ask about."
)
STOPPED = "Stopped. Nothing was written; any earlier answer is untouched."
UNREACHABLE = "Nothing answered. Check the connection, then try again."
COULD_NOT_WRITE = (
    "The answer could not be written: {reason}. Any earlier one is untouched."
)
WENT_WRONG = "The run stopped: {reason}"


def _counted(report: RunReport) -> tuple[int, int]:
    """How many albums and how many artists a run turned up."""
    albums = sum(len(gaps.albums) for gaps in report.gaps)
    artists = sum(len(gaps.artists) for gaps in report.gaps)
    return albums, artists


class Discovering:
    """Opening the discovery dialog and running what it asks for."""

    def start_discovering(
        self,
        discovery: Discovery | None,
        write: WriteDiscovery | None = None,
    ) -> None:
        """Take the service and the writer, if this window has been given any.

        A window with neither is the same shape as one with no cover chooser:
        the control is there and disabled, rather than there and dead.
        """
        self._discovery = discovery
        self._write_discovery = write
        self._discovery_dialog: DiscoveryDialog | None = None
        self._discovery_runner = DiscoveryRunner(self)
        self._discovery_runner.progressed.connect(self.discovery_progressed)
        self._discovery_runner.completed.connect(self.discovery_completed)
        self._discovery_runner.failed.connect(self.discovery_failed)

    def show_discovery_offer(self) -> None:
        """Only offer the button where there is something behind it."""
        self._tray.discover_button.setEnabled(self._discovery is not None)

    def open_discovery(self) -> None:
        """Ask what to look for; stop what is already being looked for.

        One button carrying both meanings, ruled on 2026-09-07. The dialog
        shuts the moment it has been told what to look for, so a run that takes
        eleven minutes does not hold a window open in front of everything else;
        that leaves the button as the only thing left to press, while the
        thing somebody wants of a run in progress is to stop it.
        """
        if self._discovery is None:
            return
        if self._discovery_runner.running:
            self.stop_discovery()
            return
        dialog = DiscoveryDialog(start=self.begin_discovery, parent=self)
        self._discovery_dialog = dialog
        try:
            dialog.exec()
        finally:
            self._discovery_dialog = None

    def begin_discovery(self, ticked: tuple[str, ...]) -> None:
        """Start a run over the artists inside these genres."""
        if self._discovery is None:
            return
        self._discovery_runner.start(self._discovery, self._all_albums, ticked)
        self._tray.discover_button.setToolTip(STOP_DISCOVERY_TOOLTIP)

    def stop_discovery(self) -> None:
        """Ask a running discovery to give up at its next boundary.

        The bar says so at once. Giving up happens between requests rather than
        during one, so there is a moment between the press and the ending; a
        bar still counting through that moment reads as a press nobody heard.
        """
        self._discovery_runner.cancel()
        self._tray.discovery_bar.show_stopping()

    def discovery_progressed(self, progress: DiscoveryProgress) -> None:
        """Draw how far along the run is, in the tray it reports to."""
        self._tray.discovery_bar.show_progress(progress)

    def discovery_completed(self, report: RunReport) -> None:
        """Write what was found where there is anything to write, then say so."""
        self._say_about_discovery(self._settled(report))

    def discovery_failed(self, reason: str) -> None:
        """A run that could not finish says so rather than merely stopping."""
        self._say_about_discovery(WENT_WRONG.format(reason=reason))

    def _settled(self, report: RunReport) -> str:
        """What to tell somebody about a run that reached its end."""
        if report.outcome is RunOutcome.NOTHING_TO_ASK:
            return NOTHING_TO_ASK
        if report.outcome is RunOutcome.CANCELLED:
            return STOPPED
        if report.outcome is RunOutcome.UNAVAILABLE:
            return UNREACHABLE
        albums, artists = _counted(report)
        if not albums and not artists:
            return FOUND_NOTHING
        if self._write_discovery is None:
            return FOUND_NOTHING
        try:
            where = self._write_discovery(report)
        except (OSError, ValueError) as trouble:
            return COULD_NOT_WRITE.format(reason=trouble)
        return FOUND.format(albums=albums, artists=artists, where=where)

    def _say_about_discovery(self, message: str) -> None:
        """Put the ending in front of whoever asked for the run.

        The status bar rather than a dialog, since the dialog closed the moment
        the run started: putting one back on screen minutes later would land in
        front of whatever somebody had moved on to doing.
        """
        self._tray.discovery_bar.rest()
        self._tray.discover_button.setToolTip(DISCOVER_TOOLTIP)
        self.statusBar().showMessage(message)
