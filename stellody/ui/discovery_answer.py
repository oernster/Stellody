"""Showing a run's answer: the results screen over the discovery file.

Split out of `discovering.py` on 2026-10-02 when the Discover dialog's three
boxes (FR-D85) took it over the line cap. Asking and answering were already
two concerns in one mixin; this is the answering half, reached by the window
through the same name as before.
"""

from __future__ import annotations

from collections.abc import Callable

from stellody.application.discovery_ports import DiscoveryResults, GenreMemory
from stellody.application.expanding import Expansion
from stellody.application.shopping import Shopping
from stellody.domain.album import Album
from stellody.ui.expansion_worker import ExpansionRunner
from stellody.ui.genre_folds import Folds
from stellody.ui.results_dialog import ResultsDialog
from stellody.ui.settings_keys import SETTING_GENRES_OPEN_ANSWER_FILTER


class AnsweringDiscovery:
    """The results half of the window's discovery. A mixin over the window."""

    _discovery_results: DiscoveryResults | None
    _expansion: Expansion | None
    _shopping: Shopping | None
    _genre_memory: GenreMemory | None
    _results_dialog: ResultsDialog | None
    _all_albums: tuple[Album, ...]
    _note: Callable[[str], None]

    def show_discovery_results(self) -> None:
        """Open the results on what the discovery file holds.

        **Whatever it holds, including nothing.** A run that found nothing
        used to open no screen, on the reasoning that an empty dialog says
        less than a sentence in the status bar. Ruled the other way by Oliver
        on 2026-09-09, after two whole-library runs ended in one night with
        nothing in front of him: a run that took an hour reports into a strip
        nobody is watching; an empty screen at least says what was looked
        in and what could not be answered about. FR-D33.

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
        asking = (
            None
            if self._expansion is None
            else ExpansionRunner(
                self._expansion,
                note=self._note,
                years=answer.years,
                mixes=answer.including.mixes,
            )
        )
        dialog = ResultsDialog(
            answer.gaps,
            asking=asking,
            shopping=self._shopping,
            mode=self.theme_mode,
            # From the file rather than from the ticks handed over minutes
            # earlier, so what the screen says it looked in is what the run it
            # is showing actually looked in.
            ticked=answer.ticked,
            years=answer.years,
            # What the Filter control judges by: the library as it stands and
            # what earlier runs learned candidates play. FR-D54.
            library=self._all_albums,
            remembered=(
                None if self._genre_memory is None else self._genre_memory.remembered()
            ),
            parent=self,
            folds=Folds(self._settings, SETTING_GENRES_OPEN_ANSWER_FILTER),
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
