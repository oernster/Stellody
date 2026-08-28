"""Library issues, plus the tag-collision rules that produce them."""

from __future__ import annotations

from stellody.domain.health import (
    IssueKind,
    LibraryIssue,
    issue_counts,
    sorted_issues,
)
from stellody.domain.ordering import UNKNOWN_ARTIST, TrackCandidate, resolve_tracks
from stellody.domain.track import TrackSource

ALBUM = "Mozart: Requiem"
RATE = 44100


def candidate(file_name: str, **overrides: object) -> TrackCandidate:
    """A track candidate with sensible defaults for the fields under test."""
    fields: dict[str, object] = {
        "file_name": file_name,
        "source": TrackSource(path=file_name),
        "duration_ms": 1000,
        "sample_rate": RATE,
        "bit_depth": 16,
        "artists": ("Mozart",),
    }
    fields.update(overrides)
    return TrackCandidate(**fields)  # type: ignore[arg-type]


def test_issue_summaries_and_ordering() -> None:
    art = LibraryIssue(kind=IssueKind.NO_ARTWORK, album="B")
    clash = LibraryIssue(kind=IssueKind.DUPLICATE_TRACK_NUMBER, album="A")
    ordered = sorted_issues((art, clash))
    assert ordered == (clash, art)
    assert "file names" in clash.summary
    assert "cover art" in art.summary
    assert issue_counts(ordered) == {
        IssueKind.DUPLICATE_TRACK_NUMBER: 1,
        IssueKind.NO_ARTWORK: 1,
    }


def test_no_candidates_yields_nothing() -> None:
    assert resolve_tracks((), ALBUM) == ((), ())


def test_trustworthy_tags_are_kept_untouched() -> None:
    candidates = (
        candidate("02. Kyrie.flac", tag_track=2, tag_title="Kyrie"),
        candidate("01. Introitus.flac", tag_track=1, tag_title="Introitus"),
    )
    tracks, issues = resolve_tracks(candidates, ALBUM)
    assert [track.track_number for track in tracks] == [1, 2]
    assert [track.title for track in tracks] == ["Introitus", "Kyrie"]
    assert issues == ()


def test_a_bulk_overwrite_falls_back_to_file_names() -> None:
    """Every file claims track 14; the file names still carry the truth."""
    candidates = tuple(
        candidate(
            f"{number:02d}. Movement {number}.flac",
            tag_track=14,
            tag_title="Lux aeterna",
        )
        for number in range(1, 6)
    )
    tracks, issues = resolve_tracks(candidates, ALBUM)
    assert [track.track_number for track in tracks] == [1, 2, 3, 4, 5]
    assert [track.title for track in tracks] == [
        f"Movement {number}" for number in range(1, 6)
    ]
    assert len(issues) == 1
    assert issues[0].kind is IssueKind.DUPLICATE_TRACK_NUMBER
    assert issues[0].detail == "disc 1, track 14"
    assert len(issues[0].paths) == 5


def test_an_off_by_one_shift_only_moves_the_colliding_pair() -> None:
    candidates = (
        candidate("12. Save Me.flac", tag_track=12, tag_title="Save Me"),
        candidate("13. Play The Game.flac", tag_track=14, tag_title="Play the Game"),
        candidate("14. Flash.flac", tag_track=14, tag_title="Play the Game"),
    )
    tracks, issues = resolve_tracks(candidates, "Queen: Greatest Hits")
    assert [(t.track_number, t.title) for t in tracks] == [
        (12, "Save Me"),
        (13, "Play The Game"),
        (14, "Flash"),
    ]
    assert len(issues) == 1


def test_a_missing_track_number_is_taken_from_the_file_name() -> None:
    candidates = (
        candidate("03. Third.flac", tag_title="Third"),
        candidate("01. First.flac", tag_track=1, tag_title="First"),
    )
    tracks, issues = resolve_tracks(candidates, ALBUM)
    assert [track.track_number for track in tracks] == [1, 3]
    assert issues == ()


def test_a_file_name_number_already_taken_is_moved_aside() -> None:
    candidates = (
        candidate("01. Tagged.flac", tag_track=1, tag_title="Tagged"),
        candidate("01. Untagged.flac", tag_title="Untagged"),
    )
    tracks, _ = resolve_tracks(candidates, ALBUM)
    assert sorted(track.track_number for track in tracks) == [1, 2]


def test_files_with_no_ordinal_at_all_are_numbered_and_reported() -> None:
    candidates = (
        candidate("Beta.flac", tag_title="Beta"),
        candidate("Alpha.flac", tag_title="Alpha"),
    )
    tracks, issues = resolve_tracks(candidates, ALBUM)
    assert [(t.track_number, t.title) for t in tracks] == [(1, "Alpha"), (2, "Beta")]
    assert [issue.kind for issue in issues] == [IssueKind.MISSING_TRACK_NUMBER]
    assert issues[0].detail == "2 file(s)"


def test_a_missing_title_falls_back_to_the_file_name() -> None:
    candidates = (candidate("05. Lacrimosa.flac", tag_track=5),)
    tracks, issues = resolve_tracks(candidates, ALBUM)
    assert tracks[0].title == "Lacrimosa"
    assert [issue.kind for issue in issues] == [IssueKind.MISSING_TITLE]


def test_a_duplicated_title_survives_when_the_numbering_is_trustworthy() -> None:
    """Two genuine takes of one title keep it while their numbers disagree."""
    candidates = (
        candidate("01. Reprise.flac", tag_track=1, tag_title="Reprise"),
        candidate("09. Reprise.flac", tag_track=9, tag_title="Reprise"),
    )
    tracks, issues = resolve_tracks(candidates, ALBUM)
    assert [track.title for track in tracks] == ["Reprise", "Reprise"]
    assert issues == ()


def test_disc_numbers_come_from_tags_or_file_names() -> None:
    candidates = (
        candidate("2-01 Second Disc.flac", tag_title="Second Disc"),
        candidate("01. First Disc.flac", tag_disc=1, tag_track=1, tag_title="First"),
    )
    tracks, _ = resolve_tracks(candidates, ALBUM)
    assert [(t.disc_number, t.track_number) for t in tracks] == [(1, 1), (2, 1)]


def test_a_zero_disc_tag_is_treated_as_the_first_disc() -> None:
    candidates = (candidate("Only.flac", tag_disc=0, tag_track=4, tag_title="Only"),)
    tracks, _ = resolve_tracks(candidates, ALBUM)
    assert tracks[0].disc_number == 1


def test_a_zero_disc_tag_survives_the_file_name_fallback() -> None:
    candidates = (candidate("Nameless.flac", tag_disc=0, tag_title="Nameless"),)
    tracks, _ = resolve_tracks(candidates, ALBUM)
    assert tracks[0].disc_number == 1


def test_a_track_with_no_artists_is_credited_to_an_unknown_artist() -> None:
    candidates = (
        candidate("01. Solo.flac", tag_track=1, tag_title="Solo", artists=()),
    )
    tracks, _ = resolve_tracks(candidates, ALBUM)
    assert tracks[0].artists == (UNKNOWN_ARTIST,)
