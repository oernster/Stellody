"""Editing a selection's tags, as Stellody's own state rather than as files.

The repair screen offers values the RULES worked out and asks whether to keep
them. This is the other half: values a person states, about tracks no rule
could have worked out. `domain/overrides.py` named this as a separate feature
and stopped short of it deliberately; this is that feature, built on the same
table so one Reset takes back either kind.

**Nothing here reaches a music file.** An edit becomes an `Override` row in
Stellody's own store, exactly as an accepted correction does. The
structural test that forbids this application the tag-writing API is unchanged
and still passing. That invariant is the reason the project exists.

**A field left empty is a field left alone.** Editing several tracks at once
means saying the same thing about all of them, so the panel starts empty
wherever they disagree and empty means no statement was made. Writing every
box back would take a selection of twelve differently named tracks and give
them one title, which is the shape of damage this application was built to
undo.
"""

from __future__ import annotations

from collections.abc import Iterable

from stellody.application.ports import LibraryStore
from stellody.domain.album import Album
from stellody.domain.genres import chosen_in, stated_as
from stellody.domain.overrides import AlbumEdit, AlbumField, Override, OverrideField
from stellody.domain.text import tag_date
from stellody.domain.track import Track

# What one track can be told about itself. The album around it is edited
# elsewhere, since changing an album's name changes which album it IS and that
# has to be settled before anything is folded rather than after.
TRACK_FIELDS: tuple[OverrideField, ...] = (
    OverrideField.TITLE,
    OverrideField.ARTIST,
    OverrideField.DISC_NUMBER,
    OverrideField.TRACK_NUMBER,
)


def shown_for(tracks: Iterable[Track], field: OverrideField) -> str:
    """What the panel shows for a field across a selection.

    The value where every track agrees; empty where they do not. Empty is not
    "they have no value", it is "no one value to show", which is the same
    thing as far as an edit is concerned: leaving it alone is what both mean.
    """
    stated = {_current(track, field) for track in tracks}
    return stated.pop() if len(stated) == 1 else ""


def _current(track: Track, field: OverrideField) -> str:
    """What one track holds for a field, as the text a panel would show."""
    if field is OverrideField.TITLE:
        return track.title
    if field is OverrideField.ARTIST:
        return track.artist_text
    if field is OverrideField.DISC_NUMBER:
        return str(track.disc_number)
    return str(track.track_number)


def _usable(field: OverrideField, value: str) -> bool:
    """Whether a typed value could be held by a track at all.

    A number that is not a counting number is refused here rather than written
    and dropped later. `domain/overrides.py` drops an unusable pin on the way
    in to the library, which is the right last defence; refusing it at the
    point somebody typed it is what lets them be told.
    """
    if field not in {OverrideField.DISC_NUMBER, OverrideField.TRACK_NUMBER}:
        return bool(value.strip())
    return value.strip().isdigit() and int(value.strip()) > 0


# What an album can be told about itself. Kept apart from the track fields
# because these are what the album is IDENTIFIED by: stating one changes which
# album this is, so it is settled before anything is folded rather than after.
ALBUM_FIELDS: tuple[AlbumField, ...] = (
    AlbumField.ALBUM_ARTIST,
    AlbumField.TITLE,
    AlbumField.DATE,
    AlbumField.GENRE,
)


def folders_of(album: Album) -> tuple[str, ...]:
    """Every folder this album's music sits in, in the form an edit is keyed by.

    An album is not one folder. A release split across CD1 and CD2 folders is
    one album already, so stating something about it has to reach both: state
    it against one alone and that folder alone would move, splitting the album
    it was meant to describe.

    Derived by the same normalisation the scan uses when it records a folder,
    so the two forms of the same path cannot come to disagree.
    """
    found: list[str] = []
    for track in album.ordered_tracks():
        parts = [
            part for part in track.source.path.replace("\\", "/").split("/") if part
        ]
        folder = "/".join(parts[:-1])
        if folder and folder not in found:
            found.append(folder)
    return tuple(found)


def stated_value(field: AlbumField, value: str) -> str:
    """What a typed value becomes before it is written down.

    A date is reduced to the day it names, so pasting a tag copied from
    somewhere else cannot put a meaningless time back into the store the scan
    has just been taught to keep out of it.

    A genre is reduced to the catalogue names it holds, written in catalogue
    order. That is what lets the same question be asked of what the panel SHOWS
    as of what it was given: an album tagged `pop` and a ticked Pop box are the
    same statement, so keeping a panel nobody touched writes nothing. A tag
    naming nothing in the catalogue reduces to nothing, which is also the right
    answer, since no box could have been ticked for it.

    Every other field is taken as it was typed, trimmed alone.
    """
    trimmed = value.strip()
    if field is AlbumField.DATE:
        return tag_date(trimmed)
    if field is AlbumField.GENRE:
        return stated_as(chosen_in(trimmed))
    return trimmed


def album_shown_for(album: Album, field: AlbumField) -> str:
    """What the panel shows for one of an album's own fields."""
    if field is AlbumField.ALBUM_ARTIST:
        return album.identity.album_artist
    if field is AlbumField.TITLE:
        return album.identity.title
    if field is AlbumField.DATE:
        return album.identity.date
    return album.genre


class TagEditing:
    """Records what somebody states about a selection of tracks."""

    def __init__(self, store: LibraryStore) -> None:
        self._store = store

    @staticmethod
    def album_edits_for(
        album: Album, stated: dict[AlbumField, str]
    ) -> tuple[AlbumEdit, ...]:
        """What stating these values about this album would record.

        Only what differs is recorded, so a panel opened and kept without
        anything being changed writes nothing at all. One statement reaches
        every folder the album spans, since a release in two disc folders is
        one album and has to stay one.
        """
        wanted = [
            (field, stated_value(field, value))
            for field, value in stated.items()
            if stated_value(field, value)
            and stated_value(field, value)
            != stated_value(field, album_shown_for(album, field))
        ]
        return tuple(
            AlbumEdit(folder, field, value)
            for folder in folders_of(album)
            for field, value in wanted
        )

    def state_album(self, album: Album, stated: dict[AlbumField, str]) -> int:
        """Record these values about this album; how many were written.

        Giving an album the artist and title another already carries makes the
        two one album, since that pair is what an album is identified by. The
        merged album then reads the rating held against that identity, which is
        the rating of the album this one was stated INTO.
        """
        edits = self.album_edits_for(album, stated)
        if edits:
            self._store.state_album_edits(edits)
        return len(edits)

    @staticmethod
    def refused(stated: dict[OverrideField, str]) -> tuple[OverrideField, ...]:
        """The fields whose typed value no track could hold."""
        return tuple(
            field
            for field, value in stated.items()
            if value.strip() and not _usable(field, value)
        )

    @staticmethod
    def edits_for(
        album: str, tracks: Iterable[Track], stated: dict[OverrideField, str]
    ) -> tuple[Override, ...]:
        """What stating these values about these tracks would record.

        A number field states one number about every track selected, which is
        what somebody correcting a disc number means. A title states one title
        about every track selected too, which is only ever what somebody means
        about ONE track; the panel is what stops that being offered for many,
        rather than a rule here that would have to guess at intent.
        """
        edits: list[Override] = []
        for track in tracks:
            for field, value in stated.items():
                text = value.strip()
                if not text or not _usable(field, text):
                    continue
                if text == _current(track, field):
                    continue
                edits.append(Override(album, field, text, track.source.path))
        return tuple(edits)

    def state(
        self, album: str, tracks: Iterable[Track], stated: dict[OverrideField, str]
    ) -> int:
        """Record these values about these tracks; how many were written."""
        edits = self.edits_for(album, tracks, stated)
        if edits:
            self._store.accept_overrides(edits)
        return len(edits)
