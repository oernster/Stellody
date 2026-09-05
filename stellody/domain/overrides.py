"""Corrections a listener has accepted, kept as Stellody's own state.

The library already shows corrected values. The store holds RAW tags and
resolution happens on load, so a damaged album is read, worked out and displayed
without a music file being touched. What was missing is anywhere to record that
a correction has been ACCEPTED, so the same findings were recomputed and
re-reported at every start.

An override is that record: what it applies to, which field, then the value.
Resolution gains a third layer applied in this order: the raw tags, then the
automatic rules, then the accepted overrides on top.

**An override never reaches a music file.** It is Stellody's own state and lives
where Stellody's own state lives, which is the invariant the whole project
exists for. Nothing here writes anything; this module is values and rules.

**What is pinned is the value the rule proposed.** Accepting is a listener
saying "yes, keep that" about a correction Stellody already made, so an accepted
override holds the same value the rules produced and the library does not move
when one is added. What it changes is that the finding stops being reported and
the value stops depending on the rule that first suggested it. Preferring a
value of one's own over the rule's is a different feature and is not this one.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import StrEnum

from stellody.domain.health import IssueKind
from stellody.domain.text import split_artists
from stellody.domain.track import Track

# Album-wide rather than about one file, so an override carrying this field
# names no path.
ALBUM_WIDE = ""


class OverrideField(StrEnum):
    """Which resolved value an override pins."""

    DISC_NUMBER = "disc-number"
    TRACK_NUMBER = "track-number"
    TITLE = "title"
    ARTIST = "artist"
    ALBUM_ARTIST = "album-artist"


# What each kind of finding proposes a value for. A kind ABSENT from this table
# proposes nothing, so it can be reported and never accepted: there is no
# artwork to accept where none was found and no reading to accept where the file
# could not be read. That absence is the rule, rather than a second list that
# could come to disagree with this one.
FIELD_FOR_KIND: dict[IssueKind, OverrideField] = {
    IssueKind.DUPLICATE_TRACK_NUMBER: OverrideField.TRACK_NUMBER,
    IssueKind.MISSING_TRACK_NUMBER: OverrideField.TRACK_NUMBER,
    IssueKind.DISC_NUMBER_CONFLICT: OverrideField.DISC_NUMBER,
    IssueKind.MISSING_TITLE: OverrideField.TITLE,
    IssueKind.MISSING_ALBUM_ARTIST: OverrideField.ALBUM_ARTIST,
}

# The fields that describe one file rather than the album around it. An
# album-wide field is pinned once and names no path.
TRACK_FIELDS = frozenset(
    {
        OverrideField.DISC_NUMBER,
        OverrideField.TRACK_NUMBER,
        OverrideField.TITLE,
        OverrideField.ARTIST,
    }
)

# What a finding can propose, which is not everything an override can hold.
# The artist is here because somebody may TYPE one; no rule ever infers it, so
# nothing proposes it and it appears in no report. The two lists are kept apart
# rather than merged, since a field the rules cannot work out is exactly the
# field a person most needs to be able to state.
PROPOSED_FIELDS = frozenset(FIELD_FOR_KIND.values())


class AlbumField(StrEnum):
    """Which part of an album's own description an edit states.

    A separate vocabulary from `OverrideField` rather than more members on it,
    because these are applied at a different moment and keyed by a different
    thing. Sharing one enum would let a value meant for one layer be handed to
    the other, which would be accepted and then quietly do nothing.
    """

    ALBUM_ARTIST = "album-artist"
    TITLE = "album-title"
    DATE = "date"
    GENRE = "genre"


@dataclass(frozen=True, slots=True)
class AlbumEdit:
    """One stated part of an album's description, against the folder holding it.

    **Keyed by the folder rather than by the album's handle**, which is the
    whole reason this is a separate thing from `Override`. A handle is a digest
    of the album artist, the title and the year, so an edit to any of those
    changes the handle: an edit keyed by the handle would answer to the album
    it had already stopped describing and would undo itself the instant it took
    effect. A folder is where the music actually sits, so it says the same
    thing before and after.

    That keying is also what makes two albums fold together. Give one the
    artist and title another already carries and they resolve to one handle,
    which is how two disc folders of a single release have always become one
    album. The merged album reads the rating held against that handle, so the
    album edited INTO another takes the rating of the one it joined.
    """

    folder: str
    field: AlbumField
    value: str

    def __post_init__(self) -> None:
        if not self.folder:
            raise ValueError("an album edit needs a folder to belong to")
        if not self.value:
            raise ValueError("an album edit with no value states nothing")


# What the album edits say, keyed for one lookup while entries are walked.
AlbumEditIndex = dict[tuple[str, AlbumField], str]


def album_index(edits: tuple[AlbumEdit, ...]) -> AlbumEditIndex:
    """Arrange album edits for the question assembly asks of them.

    A later edit for the same folder and field replaces an earlier one, so a
    set carrying both cannot resolve differently depending on which was read
    first. That is the rule `index` follows for the track-level table and the
    two are deliberately the same.
    """
    return {(edit.folder, edit.field): edit.value for edit in edits}


def can_be_accepted(kind: IssueKind) -> bool:
    """Whether this kind of finding proposes a value somebody could accept."""
    return kind in FIELD_FOR_KIND


@dataclass(frozen=True, slots=True)
class Override:
    """One accepted correction: what it applies to, which field, the value.

    The album is named by its identity handle rather than by a path, so a folder
    rename or a re-rip does not orphan it, which is the reason artwork and
    ratings are keyed the same way. The path is carried alongside as the
    tiebreak, so two identical albums in one library can still be told apart and
    so a track-level pin names the file it is about.
    """

    album: str
    field: OverrideField
    value: str
    path: str = ALBUM_WIDE

    def __post_init__(self) -> None:
        if not self.album:
            raise ValueError("an override needs an album to belong to")
        if not self.value:
            raise ValueError("an override with no value pins nothing")
        if self.field in TRACK_FIELDS and not self.path:
            raise ValueError(f"{self.field} is about one file, so it needs a path")
        if self.field not in TRACK_FIELDS and self.path:
            raise ValueError(f"{self.field} is album wide, so it takes no path")


# What resolution asks of the accepted set, keyed for one lookup rather than a
# walk per track: the album handle, the file the value is about (empty where the
# field is album wide) and the field itself.
AcceptedIndex = dict[tuple[str, str, OverrideField], str]


def index(accepted: tuple[Override, ...]) -> AcceptedIndex:
    """Arrange overrides for the questions resolution asks of them.

    Built once per assembly rather than per track. A later override for the same
    album, path and field replaces an earlier one, so a set carrying both cannot
    resolve differently depending on which was read first.
    """
    return {
        (override.album, override.path, override.field): override.value
        for override in accepted
    }


def value_for(
    accepted: AcceptedIndex, album: str, field: OverrideField, path: str = ALBUM_WIDE
) -> str | None:
    """The pinned value for one field; None where nothing has been accepted."""
    return accepted.get((album, path, field))


def covers(
    accepted: AcceptedIndex, album: str, field: OverrideField, paths: tuple[str, ...]
) -> bool:
    """Whether every file a finding names has been accepted for its field.

    A finding is silenced only where the whole of it has been accepted. Half an
    accepted finding is still a finding: reporting it would be wrong about what
    is outstanding and dropping it would hide the part nobody answered.

    A finding naming no path is album wide, so one pin covers it.
    """
    if not paths:
        return value_for(accepted, album, field) is not None
    return all(value_for(accepted, album, field, path) is not None for path in paths)


def _as_number(value: str | None) -> int | None:
    """A pinned number; None where nothing is pinned or what is stored is not one.

    A store can be edited by hand and a column holds text. The asymmetry is the
    reason this refuses rather than raises: ignoring one unreadable pin costs a
    correction nobody sees applied, while raising costs the whole library, which
    would then fail to assemble at every start with no way back in.
    """
    if value is None:
        return None
    try:
        return int(value)
    except ValueError:
        return None


def applied(
    tracks: tuple[Track, ...], album: str, accepted: AcceptedIndex
) -> tuple[Track, ...]:
    """The tracks with every accepted pin laid over them.

    This is the third layer: the raw tags, then the automatic rules that
    produced these tracks, then whatever has been accepted on top. Where the
    pinned value is the one the rules already produced, which is what accepting
    a proposal records, nothing moves; the value simply stops depending on the
    rule that suggested it.

    A pin that would make a track invalid, a track number of nought or a title
    of nothing, is dropped rather than applied. The store is not the place a
    listener is told about a value no track could hold.
    """
    if not accepted:
        return tracks
    laid: list[Track] = []
    for track in tracks:
        path = track.source.path
        disc = _as_number(value_for(accepted, album, OverrideField.DISC_NUMBER, path))
        number = _as_number(
            value_for(accepted, album, OverrideField.TRACK_NUMBER, path)
        )
        title = value_for(accepted, album, OverrideField.TITLE, path)
        artist = value_for(accepted, album, OverrideField.ARTIST, path)
        if disc is None and number is None and title is None and artist is None:
            laid.append(track)
            continue
        # One field holding several names, split the way a tag holding several
        # is split, so a typed "Sasha; Kicks Like a Mule" reaches the library
        # as the two artists it names rather than as one artist with a
        # semicolon in it.
        credited = split_artists(artist) if artist is not None else ()
        try:
            laid.append(
                replace(
                    track,
                    disc_number=disc if disc is not None else track.disc_number,
                    track_number=(number if number is not None else track.track_number),
                    title=title if title is not None else track.title,
                    artists=credited if credited else track.artists,
                )
            )
        except ValueError:
            laid.append(track)
    return tuple(laid)
