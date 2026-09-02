"""The third layer: accepted corrections laid over the rules during assembly.

Accepting is a listener saying "yes, keep that" about a correction Stellody
already made, so the library holds still while the finding stops being reported.
These are the rules of that, checked against a real assembly rather than against
the pieces on their own.
"""

from __future__ import annotations

from stellody.domain.grouping import SourceEntry, _is_answered, assemble_albums
from stellody.domain.health import IssueKind, LibraryIssue
from stellody.domain.ordering import TrackCandidate
from stellody.domain.overrides import Override, OverrideField, index
from stellody.domain.track import TrackSource

RATE = 44100
PARENT = "H:/Music/Portishead"
FOLDER = "Dummy"


def entry(file_name: str, **tags: object) -> SourceEntry:
    """One source in a single-folder album, with whatever tags a test needs."""
    candidate = TrackCandidate(
        file_name=file_name,
        source=TrackSource(path=f"{PARENT}/{FOLDER}/{file_name}"),
        duration_ms=1000,
        sample_rate=RATE,
        bit_depth=16,
        tag_disc=tags.pop("tag_disc", None),  # type: ignore[arg-type]
        tag_track=tags.pop("tag_track", None),  # type: ignore[arg-type]
        tag_title=tags.pop("tag_title", file_name),  # type: ignore[arg-type]
        artists=("Portishead",),
    )
    fields: dict[str, object] = {
        "folder_name": FOLDER,
        "parent_path": PARENT,
        "parent_name": "Portishead",
        "candidate": candidate,
        "album": "Dummy",
    }
    fields.update(tags)
    return SourceEntry(**fields)  # type: ignore[arg-type]


def path_of(file_name: str) -> str:
    """The full path a file name stands for in these albums."""
    return f"{PARENT}/{FOLDER}/{file_name}"


def handle_for(entries: tuple[SourceEntry, ...]) -> str:
    """The album handle an assembly produces, read from the assembly itself.

    Taken from the run rather than digested here, so a test cannot pass while
    disagreeing with the identity the application would really key on.
    """
    albums, _ = assemble_albums(entries)
    return albums[0].identity.handle


def kinds(issues: tuple[LibraryIssue, ...]) -> set[IssueKind]:
    """Which kinds of finding an assembly reported."""
    return {issue.kind for issue in issues}


COLLIDING = (
    entry("01 Mysterons.flac", tag_track=1, tag_title="Mysterons"),
    entry("02 Sour Times.flac", tag_track=1, tag_title="Sour Times"),
)


class TestAFindingStopsBeingOneOnceAccepted:
    def test_an_album_artist_finding_is_reported_while_nothing_is_accepted(
        self,
    ) -> None:
        _, issues = assemble_albums(COLLIDING)
        assert IssueKind.MISSING_ALBUM_ARTIST in kinds(issues)

    def test_pinning_the_album_artist_silences_it(self) -> None:
        album = handle_for(COLLIDING)
        accepted = (Override(album, OverrideField.ALBUM_ARTIST, "Portishead"),)
        _, issues = assemble_albums(COLLIDING, accepted)
        assert IssueKind.MISSING_ALBUM_ARTIST not in kinds(issues)

    def test_pinning_every_colliding_file_silences_the_collision(self) -> None:
        album = handle_for(COLLIDING)
        accepted = (
            Override(
                album, OverrideField.TRACK_NUMBER, "1", path_of("01 Mysterons.flac")
            ),
            Override(
                album, OverrideField.TRACK_NUMBER, "2", path_of("02 Sour Times.flac")
            ),
        )
        _, issues = assemble_albums(COLLIDING, accepted)
        assert IssueKind.DUPLICATE_TRACK_NUMBER not in kinds(issues)

    def test_pinning_half_of_it_leaves_it_reported(self) -> None:
        """Dropping it would hide the file nobody answered for."""
        album = handle_for(COLLIDING)
        accepted = (
            Override(
                album, OverrideField.TRACK_NUMBER, "1", path_of("01 Mysterons.flac")
            ),
        )
        _, issues = assemble_albums(COLLIDING, accepted)
        assert IssueKind.DUPLICATE_TRACK_NUMBER in kinds(issues)

    def test_a_pin_on_another_album_silences_nothing(self) -> None:
        accepted = (Override("not this album", OverrideField.ALBUM_ARTIST, "Someone"),)
        _, issues = assemble_albums(COLLIDING, accepted)
        assert IssueKind.MISSING_ALBUM_ARTIST in kinds(issues)


class TestWhatAPinDoesToTheAlbum:
    def test_accepting_what_the_rule_produced_leaves_the_album_alone(self) -> None:
        plain, _ = assemble_albums(COLLIDING)
        album = plain[0].identity.handle
        accepted = tuple(
            Override(
                album,
                OverrideField.TRACK_NUMBER,
                str(track.track_number),
                track.source.path,
            )
            for track in plain[0].tracks
        )
        pinned, _ = assemble_albums(COLLIDING, accepted)
        assert pinned[0].tracks == plain[0].tracks

    def test_a_pinned_number_moves_the_track_and_the_album_reorders(self) -> None:
        """A pin that moves a track puts it where it now belongs, not where it was."""
        album = handle_for(COLLIDING)
        accepted = (
            Override(
                album, OverrideField.TRACK_NUMBER, "9", path_of("01 Mysterons.flac")
            ),
        )
        albums, _ = assemble_albums(COLLIDING, accepted)
        numbers = [track.track_number for track in albums[0].tracks]
        assert numbers == sorted(numbers)
        assert numbers[-1] == 9

    def test_a_pinned_title_is_shown(self) -> None:
        album = handle_for(COLLIDING)
        accepted = (
            Override(album, OverrideField.TITLE, "Mine", path_of("01 Mysterons.flac")),
        )
        albums, _ = assemble_albums(COLLIDING, accepted)
        assert "Mine" in {track.title for track in albums[0].tracks}


class TestAKindThatProposesNothing:
    def test_it_can_never_be_answered(self) -> None:
        """Assembly does not raise these today; a new kind must not slip through.

        The guard is what stops a kind added later being silenced by an
        accident of the table rather than by a decision somebody made.
        """
        issue = LibraryIssue(
            kind=IssueKind.UNREADABLE_FILE, album="Portishead - Dummy", paths=("x",)
        )
        assert not _is_answered(issue, "any album", index(()), {})
