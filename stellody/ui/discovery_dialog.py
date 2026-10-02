"""Asking what the library is missing, in the genres somebody chose.

The same catalogue the filter asks with, for the same reason: two grids built
from one catalogue cannot come to disagree, while a second vocabulary invented
here would.

**Ticking is what scopes the run, so it is what the dialog is mostly made of.**
A run over the whole library names 327 artists to two public catalogues; a run
over Folk names one. The ticks are the difference between those, which is why
the action cannot be pressed until at least one box is.

**It asks, then it leaves.** Ruled on 2026-09-07. A run takes minutes at the
rate the catalogues permit; a dialog held open for all of them is one
somebody has to work around to carry on listening. Pressing Find hands the
ticks over and closes; the run reports to the bar in the tray and the button
that started it becomes the one that stops it. So this dialog knows nothing
about a run: it cannot report on one, cannot cancel one and does not know
whether one is under way.

**It asks whether to widen the run to compilations, with the price beside it.**
Ruled by Oliver on 2026-09-13: the artists on compilations are only asked about
when somebody ticks for them, since doing so can add minutes. The price arrives
already worked out, so this still holds no memory and no pace of its own.
FR-D51, FR-D52.

**It holds no service and reaches no network.** Starting is handed in, so the
whole dialog can be driven with nothing behind it.
"""

from __future__ import annotations

import datetime
from collections.abc import Callable

from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from stellody.application.compilation_cost import Cost
from stellody.domain.estimating import SECONDS_PER_MINUTE, rounded_minutes
from stellody.domain.including import OWN_ALBUMS, Including
from stellody.domain.release_years import ReleaseYears, YearRefusal
from stellody.shared import resources
from stellody.ui.dialogs import (
    CLOSE_ICON,
    CONTROL_ICON_PX,
    FirstStopDialog,
    title_label,
    wearing,
)
from stellody.ui.genre_folds import Folds
from stellody.ui.genre_grid import ASKING, GenreGrid
from stellody.ui.icons import plain_icon, struck_through
from stellody.ui.ringed_check import RingedCheckBox
from stellody.ui.year_fields import YearFields, refusal_words

TITLE = "Discover new music"
FIND_LABEL = "Find"
CLOSE_LABEL = "Close"
# One control naming what a press would do, which is the convention both trays
# already follow. Ticking every box in the catalogue by hand to ask about a
# whole library is the kind of tidying a dialog should do for somebody; once
# they are all ticked the only thing left to want is them gone. A push button
# rather than one more tick box, so it cannot read as one more genre: the same
# shape the filter dialog's
# Clear already has, in the same place.
SELECT_ALL_LABEL = "Select all"
CLEAR_LABEL = "Clear"
# Reached by name rather than through a getter in `resources`, which is how
# every dialog control's picture is reached: the getters are swept by the guide
# test, which is about the controls on the two trays.
SELECT_ALL_ICON = "select-all.png"
# What the dialog says before anything has been asked of it. It names where the
# answer will appear, since the dialog will not be there to show it.
RESTING = (
    "Tick the genres to find similar music in, then press Find. "
    "This closes; the toolbar reports on the search."
)
# The least the dialog is drawn at; the grid widens it past this where its
# open categories need the room, the same as the filter dialog.
DIALOG_WIDTH_PX = 700
APART_PX = 12
# The three boxes that say what else a run takes in, under one heading.
# Ruled by Oliver on 2026-10-02: one box used to mean the first two. FR-D85.
INCLUDE_HEADING = "Include:"
# The artists on compilations. FR-D51. Named for what such albums are filed
# under, since that is what somebody will look for.
CREDITS_LABEL = "Artists on compilations (Various Artists)"
# The other volumes of the compilations held. FR-D69, FR-D82.
SERIES_LABEL = "Other volumes of series"
# DJ mixes in an artist's own list. FR-D80.
MIXES_LABEL = "DJ mixes"
# What ticking the boxes would cost, said beneath them. FR-D52. The minutes are
# arithmetic at the pace the catalogue permits, so the sentence names what makes
# a real run longer rather than passing a floor off as a forecast.
NOTHING_NEW = (
    "Every artist and series on compilations in these genres has been looked up "
    "already, so including them asks nothing new."
)
# The artists and the series still to look up, named apart since a series is
# not an artist. FR-D52, FR-D69.
ONE_ARTIST = "one artist"
SOME_ARTISTS = "{count} artists"
ONE_SERIES = "one series"
SOME_SERIES = "{count} series"
BOTH = "{artists} and {series}"
NOT_LOOKED_UP = "{what} on compilations in these genres {verb} not been looked up yet"
HAS = "has"
HAVE = "have"
UNDER_A_MINUTE = "under a minute more"
ABOUT_A_MINUTE = "about a minute more"
ABOUT_MINUTES = "about {minutes} minutes more"
COST = "{names}: {time} at the pace MusicBrainz allows, longer when it is busy."
# A single name or a single minute reads as "one" rather than "1 artists".
ONE = 1


def _counted(count: int, one: str, some: str) -> str:
    """A count in words: "one" for a single one rather than "1"."""
    return one if count == ONE else some.format(count=count)


def _still_to_look_up(cost: Cost) -> str:
    """Who and what is still to be looked up, as the start of a sentence."""
    artists = _counted(cost.names, ONE_ARTIST, SOME_ARTISTS)
    series = _counted(cost.series, ONE_SERIES, SOME_SERIES)
    if cost.names and cost.series:
        what = BOTH.format(artists=artists, series=series)
    else:
        what = artists if cost.names else series
    single = cost.names + cost.series == ONE
    said = NOT_LOOKED_UP.format(what=what, verb=HAS if single else HAVE)
    return said[0].upper() + said[1:]


def cost_sentence(cost: Cost) -> str:
    """What including compilations would add, in the words beneath the box."""
    if not cost.names and not cost.series:
        return NOTHING_NEW
    names = _still_to_look_up(cost)
    minutes = rounded_minutes(cost.seconds)
    if cost.seconds < SECONDS_PER_MINUTE:
        said = UNDER_A_MINUTE
    elif minutes == ONE:
        said = ABOUT_A_MINUTE
    else:
        said = ABOUT_MINUTES.format(minutes=minutes)
    return COST.format(names=names, time=said)


def _start_nothing(
    _genres: tuple[str, ...], _including: Including, _years: ReleaseYears
) -> None:
    """A dialog handed no run to start starts nothing."""


def _this_year() -> int:
    """The current year, which the latest year worth asking about follows."""
    return datetime.datetime.now(datetime.UTC).astimezone().year


def _keep_nothing(_including: Including) -> None:
    """A dialog handed nowhere to remember the boxes remembers nothing."""


class DiscoveryDialog(FirstStopDialog):
    """Collects the genres to search in, then hands them over and closes."""

    def __init__(
        self,
        start: Callable[
            [tuple[str, ...], Including, ReleaseYears], None
        ] = _start_nothing,
        parent: QWidget | None = None,
        including: Including = OWN_ALBUMS,
        cost: Callable[[tuple[str, ...], Including], Cost] | None = None,
        remember: Callable[[Including], None] = _keep_nothing,
        this_year: int | None = None,
        folds: Folds | None = None,
    ) -> None:
        super().__init__(parent)
        self._start = start
        self._remember = remember
        # True while Select all moves every box, so each does not price alone.
        self._sweeping = False
        # Read once as the dialog opens, since the latest year worth asking
        # about follows it; handed in by a test standing in another year.
        self._this_year = _this_year() if this_year is None else this_year
        # What including compilations would add for a set of ticks; None where
        # the window has no memory to price it from, so no line is shown
        # rather than a guess. FR-D52.
        self._cost = cost
        # Resolved once rather than per toggle: a sweep moves every box and each
        # of them asks this control to say what it now offers.
        self._sweep_art = resources.find_asset(SELECT_ALL_ICON)
        self.setWindowTitle(TITLE)
        self.setMinimumWidth(DIALOG_WIDTH_PX)
        outer = QVBoxLayout(self)
        # The same words as the title bar, from the same constant: two spellings
        # of one name is the kind of drift nobody notices until it is shipped.
        self.title = title_label(TITLE, self)
        outer.addWidget(self.title)
        outer.addSpacing(APART_PX)
        self.grid = GenreGrid("", self, manner=ASKING, folds=folds)
        for box in self.grid.boxes.values():
            box.toggled.connect(self._ticks_changed)
        outer.addWidget(self.grid)
        outer.addSpacing(APART_PX)
        # Built after the genres and before the buttons, which is also where
        # Tab reaches them: what to look in, what else to take in, then go.
        outer.addWidget(QLabel(INCLUDE_HEADING, self))
        self.credits = self._choice(CREDITS_LABEL, including.credits, outer)
        self.series = self._choice(SERIES_LABEL, including.series, outer)
        self.mixes = self._choice(MIXES_LABEL, including.mixes, outer)
        self.cost_line = QLabel("", self)
        self.cost_line.setWordWrap(True)
        self.cost_line.setHidden(cost is None)
        outer.addWidget(self.cost_line)
        outer.addSpacing(APART_PX)
        # Which years to offer music from, both optional and empty on every
        # opening. After the genres, since those choose who is asked; these
        # only choose what comes back. FR-D58.
        self.years = YearFields(self)
        self.years.changed.connect(self._ticks_changed)
        outer.addWidget(self.years)
        outer.addSpacing(APART_PX)
        self.message = QLabel(RESTING, self)
        self.message.setWordWrap(True)
        outer.addWidget(self.message)
        outer.addLayout(self._buttons())
        self._ticks_changed()

    def _buttons(self) -> QHBoxLayout:
        """The sweep away to the left, then away, then the one that works."""
        row = QHBoxLayout()
        self.select_button = QPushButton(SELECT_ALL_LABEL, self)
        self.select_button.setIconSize(QSize(CONTROL_ICON_PX, CONTROL_ICON_PX))
        self.select_button.clicked.connect(self._select_or_clear)
        row.addWidget(self.select_button)
        row.addStretch()
        self.close_button = wearing(
            QPushButton(CLOSE_LABEL, self), resources.find_asset(CLOSE_ICON)
        )
        self.close_button.clicked.connect(self.reject)
        row.addWidget(self.close_button)
        # The same picture the control that opens this dialog wears, since a
        # press here is the thing that button promised.
        self.find_button = wearing(
            QPushButton(FIND_LABEL, self), resources.discover_icon_path()
        )
        self.find_button.setDefault(True)
        self.find_button.clicked.connect(self._find)
        row.addWidget(self.find_button)
        return row

    def _choice(self, label: str, ticked: bool, outer: QVBoxLayout) -> RingedCheckBox:
        """One of the three boxes, remembered and priced as it is moved."""
        box = RingedCheckBox(label, self)
        box.setChecked(ticked)
        box.toggled.connect(self._choices_changed)
        outer.addWidget(box)
        return box

    def including(self) -> Including:
        """What the three boxes say to take in. FR-D85."""
        return Including(
            credits=self.credits.isChecked(),
            series=self.series.isChecked(),
            mixes=self.mixes.isChecked(),
        )

    def _choices_changed(self) -> None:
        """Keep the boxes as they were left; say what they now cost."""
        self._remember(self.including())
        self._price()

    def chosen(self) -> tuple[str, ...]:
        """The genres ticked, in catalogue order."""
        return self.grid.chosen()

    def _ticks_changed(self) -> None:
        """Nothing ticked is nothing to ask about, so the action goes.

        A run over no genres has no artists to look up, so offering it invites
        a press that can only report emptiness.

        The sweep says what a press would do rather than what the boxes are:
        with anything left to tick it offers to tick it; with everything
        ticked the only thing left to offer is clearing. Read off the boxes
        rather than remembered, since a listener ticking the last one by hand
        moves it without touching this.

        Years that cannot be used take the action away too and say why in
        the message line, where the dialog already talks. FR-D59.
        """
        reading = self.years.reading(self._this_year)
        refused = isinstance(reading, YearRefusal)
        self.message.setText(
            refusal_words(reading, self._this_year) if refused else RESTING
        )
        self.find_button.setEnabled(bool(self.chosen()) and not refused)
        everything = self.grid.all_ticked()
        self.select_button.setText(CLEAR_LABEL if everything else SELECT_ALL_LABEL)
        # The picture says the same thing the words do. Clearing is the sweep
        # struck through rather than a second drawing, which is the rule the
        # discovery button and every switch at the foot of the window follow:
        # the cross is one file laid over another, so a change to it reaches
        # every use at once.
        self.select_button.setIcon(
            struck_through(
                self._sweep_art, resources.negative_icon_path(), CONTROL_ICON_PX
            )
            if everything
            else plain_icon(self._sweep_art)
        )
        self._price()

    def _price(self) -> None:
        """Say what the boxes ticked would add for the genres now ticked.

        Nothing is said with no genre ticked, since a run over no genres adds
        nobody whatever the boxes say; nor with neither of the first two boxes
        ticked, since only those cost requests. FR-D85.
        """
        if self._cost is None or self._sweeping:
            return
        ticked = self.chosen()
        including = self.including()
        costly = including.credits or including.series
        self.cost_line.setText(
            cost_sentence(self._cost(ticked, including)) if ticked and costly else ""
        )

    def _select_or_clear(self) -> None:
        """Tick everything, else clear it where there is nothing left to tick.

        It does not close, for the reason the filter's Clear does not: sweeping
        and then asking is two presses, while somebody who swept by accident
        has lost nothing.

        **Priced once, not once a box.** Measured on 2026-10-02 over Oliver's
        library: one price takes 0.12 seconds and a sweep of 57 boxes asked for
        57 of them, freezing the dialog for 4.1 seconds. The price waits for
        the sweep to end; the pointer says the dialog is busy meanwhile.
        """
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        self._sweeping = True
        try:
            self.grid.set_all(not self.grid.all_ticked())
        finally:
            self._sweeping = False
            self._price()
            QApplication.restoreOverrideCursor()

    def _find(self) -> None:
        """Hand the ticked genres over, then get out of the way.

        Guarded rather than merely disabled: the action is reachable from the
        keyboard while it is off, so a run over nothing could otherwise ask two
        public catalogues about nobody. Years that cannot be used are guarded
        the same way, so a range nobody asked for is never run.
        """
        years = self.years.reading(self._this_year)
        if not self.chosen() or isinstance(years, YearRefusal):
            return
        self._start(self.chosen(), self.including(), years)
        self.accept()
