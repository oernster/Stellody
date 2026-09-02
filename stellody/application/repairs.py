"""Accepting the corrections a health report describes, then taking them back.

The report says what Stellody worked around. Accepting one is a listener saying
"yes, keep that", which records the value the rules already produced so the
finding stops being recomputed and re-read at every start.

**Accept-all is the default path, not a power-user shortcut.** 142 findings is
not a workflow and a library twice the size makes it ten times worse, so the
three granularities are all one gesture: everything the report lists, everything
in one album or one finding. They are the same call with different findings
handed to it, rather than three routines that could come to disagree.

**Nothing accepted is permanent.** The same three undo, working from what is
STORED rather than from what is displayed: once a finding has been accepted it
is no longer in the report, so there would be nothing left on screen to point
at. What is offered instead is the accepted set itself, grouped as it was
accepted, which is the same unit read from the other side.

**An override never reaches a music file.** This service reads the library and
writes to Stellody's own store, nothing else. Resetting drops a row and lets the
automatic rule show through again; there is nothing to corrupt, because the raw
tags were never altered.
"""

from __future__ import annotations

import os
from collections.abc import Iterable
from dataclasses import dataclass

from stellody.application.ports import LibraryStore
from stellody.application.scan import LibraryView
from stellody.domain.album import Album
from stellody.domain.health import LibraryIssue
from stellody.domain.overrides import (
    FIELD_FOR_KIND,
    Override,
    OverrideField,
    can_be_accepted,
)
from stellody.domain.track import Track


def _value_of(track: Track, field: OverrideField) -> str:
    """What a resolved track already says for one field.

    Read off the track rather than worked out again, so what is pinned is
    exactly what the reader was shown when they accepted it.
    """
    if field is OverrideField.TRACK_NUMBER:
        return str(track.track_number)
    if field is OverrideField.DISC_NUMBER:
        return str(track.disc_number)
    return track.title


def _tracks_by_name(albums: Iterable[Album]) -> dict[str, tuple[Track, ...]]:
    """Which tracks each file name in these albums stands for.

    A finding names file names while a pin names a full path, so the two have to
    be introduced. One name can stand for more than one track: a multi-disc
    album merged from CD1 and CD2 may hold "01 Intro.flac" in both, so every
    track wearing the name is pinned rather than a guess being made about which
    was meant. Pinning a value a track already holds costs nothing.

    Takes every album wearing the handle rather than one, because two can. The
    handle is a digest of the artist, the title and the year, so two separate
    recordings filed apart under one title share it, which classical music does
    routinely: a Mahler symphony under two conductors is two albums with one
    identity. Keeping only the last of them in a dictionary silently threw the
    other away; a finding belonging to the one thrown away then matched no file
    at all, wrote no pins and was reported again at every start however many
    times somebody accepted it.
    """
    found: dict[str, list[Track]] = {}
    for album in albums:
        for track in album.tracks:
            found.setdefault(os.path.basename(track.source.path), []).append(track)
    return {name: tuple(tracks) for name, tracks in found.items()}


@dataclass(frozen=True, slots=True)
class AcceptedGroup:
    """One album's accepted corrections for one field, as a resettable unit.

    The unit a finding becomes once it has been accepted: the same album and the
    same field, holding the pins that answered it. Grouped this way so that
    taking one back is the same size of gesture as accepting it was.
    """

    album: str
    field: OverrideField
    pins: tuple[Override, ...]

    @property
    def count(self) -> int:
        """How many files this group pins."""
        return len(self.pins)


class Repairs:
    """Accepting and resetting the corrections a health report describes."""

    def __init__(self, store: LibraryStore) -> None:
        self._store = store

    @staticmethod
    def acceptable(issues: Iterable[LibraryIssue]) -> tuple[LibraryIssue, ...]:
        """The findings that propose a value, so could be accepted at all.

        Missing artwork and an unreadable file propose nothing, so they are
        reported and never offered: there is nothing there to accept.
        """
        return tuple(issue for issue in issues if can_be_accepted(issue.kind))

    @staticmethod
    def in_album(
        issues: Iterable[LibraryIssue], album: str
    ) -> tuple[LibraryIssue, ...]:
        """The findings belonging to one album, by its handle not its label.

        The findings cluster into a few albums rather than spreading evenly, 36
        of 482 on the reference library, which is what makes this granularity
        worth having.
        """
        return tuple(issue for issue in issues if issue.album_key == album)

    def pins_for(
        self, view: LibraryView, issues: Iterable[LibraryIssue]
    ) -> tuple[Override, ...]:
        """What accepting these findings would record.

        Built from the library as it is displayed, so what is pinned is what the
        reader was looking at. A finding whose album is not in this view is
        skipped rather than guessed at.
        """
        # Every album under its handle, not one: two albums can wear the same
        # handle and a dictionary of one would drop all but the last.
        wearing: dict[str, list[Album]] = {}
        for album in view.albums:
            wearing.setdefault(album.identity.handle, []).append(album)
        named: dict[str, dict[str, tuple[Track, ...]]] = {}
        pins: list[Override] = []
        for issue in issues:
            field = FIELD_FOR_KIND.get(issue.kind)
            albums = wearing.get(issue.album_key)
            if field is None or not albums:
                continue
            if field is OverrideField.ALBUM_ARTIST:
                # Album-wide, so it carries no path and reaches every album
                # wearing the handle. That is right rather than a compromise:
                # sharing a handle means sharing the artist, so the accepted
                # value is the same for each of them.
                pins.append(
                    Override(issue.album_key, field, albums[0].identity.album_artist)
                )
                continue
            if issue.album_key not in named:
                named[issue.album_key] = _tracks_by_name(albums)
            for name in issue.paths:
                for track in named[issue.album_key].get(name, ()):
                    pins.append(
                        Override(
                            issue.album_key,
                            field,
                            _value_of(track, field),
                            track.source.path,
                        )
                    )
        return tuple(pins)

    def accept(self, view: LibraryView, issues: Iterable[LibraryIssue]) -> int:
        """Accept these findings; how many files were pinned."""
        pins = self.pins_for(view, issues)
        self._store.accept_overrides(pins)
        return len(pins)

    def accepted(self) -> tuple[AcceptedGroup, ...]:
        """What has been accepted, grouped as it was accepted.

        Ordered by album then field so the same set always reads the same way
        down a screen, rather than in whatever order the rows came back.
        """
        held: dict[tuple[str, OverrideField], list[Override]] = {}
        for pin in self._store.all_overrides():
            held.setdefault((pin.album, pin.field), []).append(pin)
        return tuple(
            AcceptedGroup(album=album, field=field, pins=tuple(pins))
            for (album, field), pins in sorted(held.items())
        )

    def reset(self, groups: Iterable[AcceptedGroup]) -> int:
        """Take these accepted corrections back; how many pins were dropped."""
        dropped = tuple(pin for group in groups for pin in group.pins)
        self._store.discard_overrides(dropped)
        return len(dropped)

    def reset_album(self, album: str) -> int:
        """Take back everything accepted in one album."""
        return self.reset(group for group in self.accepted() if group.album == album)

    def reset_everything(self) -> int:
        """Take back every accepted correction in the library."""
        return self.reset(self.accepted())
