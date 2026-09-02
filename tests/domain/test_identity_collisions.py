"""Two albums that resolve alike are told apart; everything else is untouched.

Reported from a real library. Tags alone cannot separate two recordings of one
work: a symphony under two conductors carries one composer, one title and often
one year. Both then answered to one handle, so they shared a cached cover, an
album rating and every track rating under it; a correction accepted on one was
looked up against the other and silently recorded nothing.

The second half of this matters as much as the first. Only the albums that
actually collide may move, because a handle that changes is a cover and a
rating that can no longer be found.
"""

from __future__ import annotations

from stellody.domain.grouping import SourceEntry, assemble_albums
from stellody.domain.identity import AlbumIdentity
from stellody.domain.listening import album_handle, track_handle
from stellody.domain.ordering import TrackCandidate
from stellody.domain.track import TrackSource

RATE = 44100
COMPOSER = "Gustav Mahler"
WORK = "Symphonie Nr. 2"
YEAR = "1995"


def entry(parent: str, folder: str, name: str, **tags: object) -> SourceEntry:
    """One source in a named folder, tagged as a classical rip usually is."""
    return SourceEntry(
        folder_name=folder,
        parent_path=parent,
        parent_name=COMPOSER,
        candidate=TrackCandidate(
            file_name=name,
            source=TrackSource(path=f"{parent}/{folder}/{name}"),
            duration_ms=1000,
            sample_rate=RATE,
            bit_depth=16,
            tag_track=tags.pop("tag_track", 1),  # type: ignore[arg-type]
            tag_title=name,
            artists=(COMPOSER,),
        ),
        album=WORK,
        album_artist=COMPOSER,
        date=YEAR,
    )


TWO_RECORDINGS = (
    entry("H:/Music/Mahler/Abbado", WORK, "01 Allegro.flac"),
    entry("H:/Music/Mahler/Solti", WORK, "01 Andante.flac"),
)
ONE_RECORDING = (entry("H:/Music/Mahler/Abbado", WORK, "01 Allegro.flac"),)


class TestTwoRecordingsOfOneWork:
    def test_they_assemble_as_two_albums(self) -> None:
        albums, _ = assemble_albums(TWO_RECORDINGS)
        assert len(albums) == 2

    def test_they_no_longer_share_a_handle(self) -> None:
        """Which is the defect: one handle meant one cover and one rating."""
        albums, _ = assemble_albums(TWO_RECORDINGS)
        assert albums[0].identity.handle != albums[1].identity.handle

    def test_they_no_longer_share_a_cached_cover(self) -> None:
        albums, _ = assemble_albums(TWO_RECORDINGS)
        assert albums[0].identity.art_key != albums[1].identity.art_key

    def test_they_no_longer_share_an_album_rating(self) -> None:
        albums, _ = assemble_albums(TWO_RECORDINGS)
        assert album_handle(albums[0].identity) != album_handle(albums[1].identity)

    def test_their_tracks_no_longer_share_a_rating(self) -> None:
        """A track record is the album's handle with its numbers under it."""
        albums, _ = assemble_albums(TWO_RECORDINGS)
        assert track_handle(albums[0].identity, 1, 1) != track_handle(
            albums[1].identity, 1, 1
        )

    def test_neither_is_shown_differently_for_it(self) -> None:
        """Told apart in the records, not on the screen: both read the same."""
        albums, _ = assemble_albums(TWO_RECORDINGS)
        assert albums[0].identity.label == albums[1].identity.label

    def test_the_separation_is_the_same_on_every_scan(self) -> None:
        """Derived from where each was found, so it cannot move between runs."""
        first, _ = assemble_albums(TWO_RECORDINGS)
        again, _ = assemble_albums(TWO_RECORDINGS)
        assert [album.identity.handle for album in first] == [
            album.identity.handle for album in again
        ]


class TestEverythingElseIsLeftExactlyAlone:
    """A handle that changes is a cover and a rating that cannot be found."""

    def test_an_album_nothing_collides_with_keeps_its_tag_only_handle(self) -> None:
        albums, _ = assemble_albums(ONE_RECORDING)
        plain = AlbumIdentity(album_artist=COMPOSER, title=WORK, date=YEAR)
        assert albums[0].identity.handle == plain.handle

    def test_it_keeps_its_cover_and_its_ratings_too(self) -> None:
        albums, _ = assemble_albums(ONE_RECORDING)
        plain = AlbumIdentity(album_artist=COMPOSER, title=WORK, date=YEAR)
        assert albums[0].identity.art_key == plain.art_key
        assert album_handle(albums[0].identity) == album_handle(plain)
        assert track_handle(albums[0].identity, 1, 1) == track_handle(plain, 1, 1)

    def test_an_identity_with_no_discriminator_digests_what_it_always_did(
        self,
    ) -> None:
        """Pinned to the literal digest, so a refactor cannot quietly move it.

        Read from the released build before this rule existed. If this fails,
        every rating and every cover in every library has been orphaned.
        """
        plain = AlbumIdentity(album_artist=COMPOSER, title=WORK, date=YEAR)
        assert plain.handle == "e66f6ef32e6a081d"

    def test_a_separated_album_carries_the_extra_part_and_a_plain_one_does_not(
        self,
    ) -> None:
        plain = AlbumIdentity(album_artist=COMPOSER, title=WORK, date=YEAR)
        apart = plain.told_apart_by("H:/Music/Mahler/Solti")
        assert plain.handle_parts == plain.key
        assert apart.handle_parts == plain.key + (apart.discriminator,)
        assert apart.discriminator
