"""What a library holds that can tell two artists of one name apart. FR-D09."""

from __future__ import annotations

from stellody.domain.album import Album
from stellody.domain.credit_evidence import (
    Evidence,
    EvidenceKind,
    evidence_by_artist,
    evidence_for,
    settled_by,
)
from stellody.domain.identity import AlbumIdentity
from stellody.domain.track import CD_SAMPLE_RATE, Track, TrackSource


def _album(album_artist: str, title: str, *tracks: tuple[str, str]) -> Album:
    """A held album; each track given as its title and its credit."""
    return Album(
        identity=AlbumIdentity(album_artist=album_artist, title=title),
        tracks=tuple(
            Track(
                source=TrackSource(path=f"{number}.flac"),
                disc_number=1,
                track_number=number,
                title=track_title,
                artists=(credit,),
                duration_ms=1000,
                sample_rate=CD_SAMPLE_RATE,
                bit_depth=16,
            )
            for number, (track_title, credit) in enumerate(tracks, start=1)
        ),
        genre="Electronic",
    )


def test_albums_come_before_tracks() -> None:
    """An album is the listener's own filing, so it is the stronger statement."""
    albums = (
        _album("Various Artists", "Adapt", ("Tribelune", "Anyma")),
        _album("Anyma", "Genesys (Deluxe)", ("Syren", "Anyma")),
    )
    found = evidence_for(evidence_by_artist(albums), "Anyma")
    assert found == (
        Evidence(EvidenceKind.ALBUM, "Genesys", "Anyma"),
        Evidence(EvidenceKind.TRACK, "Tribelune", "Anyma"),
        Evidence(EvidenceKind.TRACK, "Syren", "Anyma"),
    )


def test_a_part_of_a_credit_holds_the_track() -> None:
    """FR-D53 may have taken the credit apart to reach the name being settled."""
    albums = (_album("Various Artists", "Adapt", ("You Caress", "Giorgia & Avalon")),)
    found = evidence_for(evidence_by_artist(albums), "Avalon")
    assert found == (Evidence(EvidenceKind.TRACK, "You Caress", "Avalon"),)


def test_a_compilation_is_not_evidence_for_various_artists() -> None:
    albums = (_album("Various Artists", "Adapt", ("One", "Somebody")),)
    assert evidence_for(evidence_by_artist(albums), "Various Artists") == ()


def test_one_title_twice_is_one_piece() -> None:
    albums = (
        _album("Various Artists", "A", ("Circles (Extended)", "Nero")),
        _album("Various Artists", "B", ("Circles", "Nero")),
    )
    assert len(evidence_for(evidence_by_artist(albums), "Nero")) == 1


def test_an_artist_spelled_two_ways_holds_both() -> None:
    albums = (
        _album("Dennis de Laat", "First", ("Intro", "Somebody")),
        _album("Dennis De Laat", "Second", ("Outro", "Somebody")),
    )
    assert len(evidence_for(evidence_by_artist(albums), "DENNIS DE LAAT")) == 2


def test_an_artist_holding_nothing_has_no_evidence() -> None:
    assert evidence_for(evidence_by_artist(()), "Anyma") == ()


def test_the_question_is_one_for_two_spellings() -> None:
    """What is remembered is what the catalogue is asked; it is asked once."""
    typed = Evidence(EvidenceKind.TRACK, "Haul", "Christian Loffler")
    tagged = Evidence(EvidenceKind.TRACK, "haul", "Christian Löffler")
    assert typed.question == tagged.question


def test_the_kind_is_part_of_the_question() -> None:
    album = Evidence(EvidenceKind.ALBUM, "Circles", "Nero")
    track = Evidence(EvidenceKind.TRACK, "Circles", "Nero")
    assert album.question != track.question


def test_only_the_namesakes_credited_settle_anything() -> None:
    assert settled_by(("a", "b", "c"), ("b", "somebody-else")) == {"b"}
