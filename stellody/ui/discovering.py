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
from stellody.application.discovery_ports import DiscoveryResults
from stellody.application.expanding import Expansion
from stellody.application.shopping import Shopping
from stellody.application.values import DiscoveryProgress, RunOutcome, RunReport
from stellody.ui import shortfall, standing_in
from stellody.ui.discovery_dialog import DiscoveryDialog
from stellody.ui.discovery_worker import DiscoveryRunner
from stellody.ui.expansion_worker import ExpansionRunner
from stellody.ui.results_dialog import ResultsDialog
from stellody.ui.run_estimate import RunEstimate
from stellody.ui.tray_metrics import show_discovery_running

# Handed a finished run; answers where it was written. Raises where it could
# not be, which is reported rather than swallowed.
WriteDiscovery = Callable[[RunReport], object]

FOUND = (
    "Found {albums} albums and {artists} artists you do not hold. Written to {where}."
)
FOUND_NOTHING = "Nothing missing was found in those genres."
NOTHING_TO_ASK = (
    "Nothing in the library carries those genres, so there was nobody to ask about."
)
STOPPED = "Stopped. Nothing was written; any earlier answer is untouched."
# Said where a new run is asked for while the last one is still winding down.
# A request already in flight cannot be called back, so there is a moment
# after a stop when the thread is not free yet.
STILL_STOPPING = "Still stopping the last run. Try again in a moment."
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
        results: DiscoveryResults | None = None,
        expansion: Expansion | None = None,
        shopping: Shopping | None = None,
        note: Callable[[str], None] = standing_in.say_nothing,
    ) -> None:
        """Take the service and the writer, if this window has been given any.

        A window with neither is the same shape as one with no cover chooser:
        the control is there and disabled, rather than there and dead.

        The reader and the expansion are what the results dialog is made of:
        where a run is written down but nothing can read it back, the run
        still happens and the bar still reports on it; there is simply
        nothing to open afterwards.
        """
        self._discovery = discovery
        self._write_discovery = write
        self._discovery_results = results
        self._expansion = expansion
        # What takes a ticked album to a shop. A window given none opens the
        # results with both of its controls disabled.
        self._shopping = shopping
        # Where a run says what it is doing. A window given none keeps its own
        # counsel, which is what every test that is about something else
        # wants; the running application hands in the diary.
        self._discovery_note = note
        # Held so it is not collected the moment it is shown, since a dialog
        # nobody keeps a name for goes away with the call that made it.
        self._results_dialog: ResultsDialog | None = None
        # Whether a stop has been asked for and not yet arrived. A run reports
        # right up to the moment it notices, so those reports queue behind a
        # modal question and land in a burst once it closes.
        self._discovery_stopping = False
        self._discovery_dialog: DiscoveryDialog | None = None
        # How long the run has left, measured from its own pace. Held across
        # reports because the answer depends on when each stage began.
        self._discovery_estimate = RunEstimate()
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

        **A stop is not asked about.** It used to raise a question defaulting
        to No, so a press had to get past that before anything stopped.
        Measured on 2026-09-07 by tracing the real application: the question
        answered False and the run carried straight on. That is the whole of
        the defect reported three times as the stop never stopping; no
        amount of work below this line could have fixed it. A control named
        stop that stops is worth more than a run rescued from somebody who
        pressed stop deliberately.
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
        """Start a run over the artists inside these genres.

        A stopped run is abandoned rather than waited for, so there is room
        for this one at once. The runner still answers whether it took it;
        a refusal nobody is told about is a press that appears to do nothing,
        which is the defect this area has already been reported for.
        """
        if self._discovery is None:
            return
        if not self._discovery_runner.start(self._discovery, self._all_albums, ticked):
            self.statusBar().showMessage(STILL_STOPPING)
            return
        self._discovery_stopping = False
        # The last run's shortfall belongs to the last run. A new one starts
        # with nothing owed, so the button goes before the first question does
        # rather than being left to be corrected at the end.
        self.forget_shortfall()
        self._discovery_estimate.restart()
        # Written down so a complaint Qt makes later can be placed against the
        # run rather than merely against the evening. The catalogues are
        # reached from the run's own thread, which ends when it does.
        self._discovery_note(f"a discovery run started over {len(ticked)} genres")
        show_discovery_running(self._tray.discover_button, True)

    def stop_discovery(self) -> None:
        """Ask a running discovery to give up at its next boundary.

        The bar says so at once. Giving up happens between requests rather than
        during one, so there is a moment between the press and the ending; a
        bar still counting through that moment reads as a press nobody heard.
        """
        # The run is abandoned rather than asked to hurry: its thread is cut
        # loose to end in its own time, reporting to nobody. Everything below
        # is therefore what a stop IS, rather than a guess at what it will
        # shortly become.
        self._discovery_stopping = True
        self._discovery_runner.cancel()
        self._tray.discovery_bar.rest()
        show_discovery_running(self._tray.discover_button, False)
        self.statusBar().showMessage(STOPPED)

    def discovery_progressed(self, progress: DiscoveryProgress) -> None:
        """Draw how far along the run is, in the tray it reports to.

        Ignored once a stop has been asked for. The run goes on reporting
        until it reaches the check that ends it; anything it said while a
        modal question stood is delivered in one burst the moment that
        question closes. A bar that drew those would go back to counting
        after being told to stop, which is precisely what a stop that had
        not worked looks like. Reported as exactly that on 2026-09-07.
        """
        if self._discovery_stopping:
            return
        # One reading of the pace, said in both places it is wanted. The status
        # bar carries the sentence; the bar itself carries the same thing in
        # three characters, because the bar is at the top of the window and the
        # status bar is at the bottom, so somebody watching the percentage was
        # never meeting the time. Reported on 2026-09-07. FR-D35.
        said = self._discovery_estimate.about(progress)
        self._tray.discovery_bar.show_progress(progress, said.brief)
        self.statusBar().showMessage(said.sentence)

    def discovery_completed(self, report: RunReport) -> None:
        """Write what was found where there is anything to write, then say so.

        A run somebody stopped has already been reported on, at the moment
        they stopped it, so it says nothing further: the answer to a question
        nobody is waiting for any more.
        """
        self._discovery_note(f"a discovery run ended: {report.outcome.name}")
        if self._discovery_stopping:
            self._discovery_stopping = False
            return
        message, found, presented = self._settled(report)
        # Said BEFORE the results are opened, never after. The results are
        # modal, so a message set on the far side of them would appear only
        # once somebody had closed the screen it was meant to accompany; the
        # button and the bar are put back by the same call.
        self._say_about_discovery(message)
        # Offered for exactly the endings the sentence was said on, which is
        # why `_settled` answers that rather than this guessing at it a second
        # time. Set before the results open for the same reason the message
        # is: the results are modal, so anything done behind them is only met
        # once they close.
        self._offer_shortfall(report if presented else None)
        if found:
            self.show_discovery_results()

    def discovery_failed(self, reason: str) -> None:
        """A run that could not finish says so rather than merely stopping."""
        self._say_about_discovery(WENT_WRONG.format(reason=reason))

    def _settled(self, report: RunReport) -> tuple[str, bool, bool]:
        """What to tell somebody about a run that ended; what to open for it.

        Three answers, none inferred from another. The message; whether there
        are results worth opening; whether this ending PRESENTS AN ANSWER, so
        the shortfall belongs beside it.

        Only a run that WROTE a file has results worth opening: a stopped or
        unreachable run leaves the previous run's file exactly where it was,
        so showing "the file" after one would put a stale answer on screen as
        though it were this run's.

        The third is answered here rather than worked out again by the caller,
        so the sentence and the button can never disagree about which endings
        carry a shortfall.
        """
        if report.outcome is RunOutcome.NOTHING_TO_ASK:
            return NOTHING_TO_ASK, False, False
        if report.outcome is RunOutcome.CANCELLED:
            return STOPPED, False, False
        if report.outcome is RunOutcome.UNAVAILABLE:
            return UNREACHABLE, False, False
        # Only the two endings that PRESENT AN ANSWER carry the shortfall
        # sentence. A stopped or unreachable run has already said that its
        # answer is incomplete, so naming a count there would be saying it
        # twice; the ones that read as complete are the ones that mislead.
        short_by = shortfall.sentence(report)
        albums, artists = _counted(report)
        if not albums and not artists:
            return FOUND_NOTHING + short_by, False, True
        if self._write_discovery is None:
            return FOUND_NOTHING + short_by, False, True
        try:
            where = self._write_discovery(report)
        except (OSError, ValueError) as trouble:
            # An answer that could not be kept is not an answer presented,
            # so it carries neither the sentence nor the button.
            return COULD_NOT_WRITE.format(reason=trouble), False, False
        # Written first, then shown from what was written: the file is what a
        # later day would be shown from too, so showing anything else now
        # would be showing something nothing else can reproduce. FR-D28.
        return (
            FOUND.format(albums=albums, artists=artists, where=where) + short_by,
            True,
            True,
        )

    def show_discovery_results(self) -> None:
        """Open the results on what the discovery file holds.

        Nothing opens where the file holds nothing, which is a run that found
        nothing: an empty dialog says less than the sentence shown in its
        place, while still landing in front of whatever somebody had moved on
        to doing. FR-D33.

        **Modal, ruled by Oliver on 2026-09-08.** It was modeless first, on the
        reasoning that an answer arriving minutes after the question should not
        seize the application. What that cost was worse than what it bought:
        every completed run opened another screen, so runs stacked without
        limit. Closing the standing one as a new one opened was tried and did
        not hold in the running application, which is why the structure is
        being changed rather than the behaviour patched again. A modal screen
        cannot stack, because the window underneath it cannot start a second
        run while it is up. That is a guarantee rather than a repair.

        Opened from the completion handler, which is safe here and would not
        be everywhere: the runner quits its thread and WAITS for it before it
        announces the report, so there is nothing running behind this loop.
        `discovery_worker.DiscoveryRunner._on_completed` is where that order
        is set; the scan summary depends on the same property.
        """
        if self._discovery_results is None:
            return
        answer = self._discovery_results.last_run()
        if answer.is_empty:
            return
        asking = None if self._expansion is None else ExpansionRunner(self._expansion)
        dialog = ResultsDialog(
            answer.gaps,
            asking=asking,
            shopping=self._shopping,
            mode=self.theme_mode,
            # From the file rather than from the ticks handed over minutes
            # earlier, so what the screen says it looked in is what the run it
            # is showing actually looked in.
            ticked=answer.ticked,
            parent=self,
        )
        if asking is not None:
            # Parented to the dialog once there is one, so what asks the
            # questions lives exactly as long as the rows the answers go in.
            asking.setParent(dialog)
        self._results_dialog = dialog
        try:
            dialog.exec()
        finally:
            # Let go on the way out however the screen was left, so nothing
            # holds a dialog somebody has finished with. The same shape the
            # genre dialog uses.
            self._results_dialog = None
            dialog.deleteLater()

    def _say_about_discovery(self, message: str) -> None:
        """Put the ending in front of whoever asked for the run.

        The status bar rather than a dialog, since the dialog closed the moment
        the run started: putting one back on screen minutes later would land in
        front of whatever somebody had moved on to doing.
        """
        self._discovery_stopping = False
        self._tray.discovery_bar.rest()
        show_discovery_running(self._tray.discover_button, False)
        self.statusBar().showMessage(message)
