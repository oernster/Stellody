"""Asking about a candidate artist from the results; putting the answer up.

Moved out of `results_dialog.py` on 2026-09-13, when filtering the answer by
genre needed room in a module already close to the cap. The seam is a real
one: everything here is one conversation with the catalogue about one artist,
from the row being opened to what came back being written beneath it.

**What came back is kept as well as drawn.** A filter deals the pages again,
which builds every row afresh. A candidate already answered is never asked a
second time, so a row rebuilt without the answer would open onto nothing for
ever. Each answer is held by identifier instead; after a deal it is written
again into whatever rows that candidate now occupies. FR-D54.
"""

from __future__ import annotations

from PySide6.QtWidgets import QTreeWidgetItem

from stellody.domain.discovery import ReleaseGroup
from stellody.ui.results_top import ResultsTop
from stellody.ui.results_tree import (
    IDENTIFIER_ROLE,
    NAME_ROLE,
    CandidateRows,
    album_item,
    coloured,
)
from stellody.ui.results_words import (
    COULD_NOT_ASK,
    NOBODY_TO_ASK,
    NOTHING_OFFERED,
    candidate_row,
)
from stellody.ui.theme import Palette


class AskingResults:
    """Opening a candidate, with what the catalogue answers put beneath it.

    A mixin over the results dialog, which sets everything named here before
    any list can be opened.
    """

    _asking: object | None
    _answered: set[str]
    _in_flight: dict[str, str]
    _released: dict[str, tuple[ReleaseGroup, ...]]
    _rows: CandidateRows
    _colour: Palette
    top: ResultsTop

    def opened(self, item: QTreeWidgetItem) -> None:
        """Ask about a candidate artist the first time somebody opens it.

        A source artist opening is nothing to do: what it holds was found by
        the run. A candidate opened a second time is nothing to do either,
        since the answer to that question is already under it.
        """
        identifier = item.data(0, IDENTIFIER_ROLE)
        if identifier is None:
            return
        if not identifier:
            self._said_under(item, NOBODY_TO_ASK)
            return
        if identifier in self._answered or self._asking is None:
            return
        if self._asking.ask(identifier):
            self._answered.add(identifier)
            self._in_flight[identifier] = item.data(0, NAME_ROLE)
            self._say_what_is_being_asked()

    def show_releases(self, identifier: str, releases: object) -> None:
        """Put what an artist released under every row that artist occupies.

        Kept as well, for the rows a later filter builds. See the module.
        """
        albums = tuple(releases)
        self._released[identifier] = albums
        self._in_flight.pop(identifier, None)
        self._say_what_is_being_asked()
        self._write_releases(identifier, albums)

    def _replay_releases(self) -> None:
        """Write every answer kept so far into the rows just dealt."""
        for identifier, albums in self._released.items():
            self._write_releases(identifier, albums)

    def _write_releases(
        self, identifier: str, albums: tuple[ReleaseGroup, ...]
    ) -> None:
        """The albums under each of this artist's rows, replacing what was there.

        The row itself gains the count, which answers how many lines sit
        beneath it; the key above answers what they are.
        """
        for item in self._rows.get(identifier, ()):
            self._emptied(item)
            name = item.data(0, NAME_ROLE)
            item.setText(0, candidate_row(name, len(albums)))
            for album in albums:
                item.addChild(album_item(album, name, self._colour))
            if not albums:
                self._said_under(item, NOTHING_OFFERED)

    def show_failure(self, identifier: str, reason: str) -> None:
        """Say what went wrong against the artist it went wrong about.

        The rest of the answer is left exactly as it was: one artist nobody
        could look up is not a reason to lose a run that took minutes to
        make. Asked again the next time it is opened, since a service that
        refused once may well answer next time. FR-D32.
        """
        self._answered.discard(identifier)
        self._in_flight.pop(identifier, None)
        self._say_what_is_being_asked()
        for item in self._rows.get(identifier, ()):
            self._said_under(item, COULD_NOT_ASK.format(reason=reason))

    def _say_what_is_being_asked(self) -> None:
        """Put whoever is being looked up on the strip above the list."""
        self.top.say_asking(tuple(self._in_flight.values()))

    def _said_under(self, item: QTreeWidgetItem, message: str) -> None:
        """Put one line under a row, replacing whatever was under it."""
        self._emptied(item)
        item.addChild(coloured(QTreeWidgetItem([message]), self._colour.text_muted))

    @staticmethod
    def _emptied(item: QTreeWidgetItem) -> None:
        """Take everything out from under a row."""
        item.takeChildren()
