"""Two albums that resolve alike are one album: what that costs.

Tags alone cannot separate two recordings of one work: a symphony under two
conductors carries one composer, one title and often one year. They were once
told apart by where they were found, so that neither shared the other's cover
and ratings. They are now folded together instead, because the same rule is
what joins an album's audio to the bonus videos a library keeps in another
folder, which is the common case.

The second half still matters as much as the first: a handle that changes is a
cover and a rating that can no longer be found, so an album that folds with
nothing keeps exactly the handle it always had.
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
    """The cost of folding, written down rather than discovered in a library.

    Two recordings of one work, tagged alike, are now ONE album. That is not an
    oversight: folders that name the same album are folded together, which is
    what puts an album's audio and its bonus videos in one place when a library
    keeps them in two folders. Tags cannot tell these two apart, so they go the
    same way and share a cover, a rating and any accepted correction.

    Held as tests so that whoever reverses this decision one day sees exactly
    what they are buying back.
    """

    def test_they_assemble_as_one_album(self) -> None:
        albums, _ = assemble_albums(TWO_RECORDINGS)
        assert len(albums) == 1

    def test_that_album_holds_both_recordings(self) -> None:
        """Nothing is dropped by folding; both files are still in the library."""
        albums, _ = assemble_albums(TWO_RECORDINGS)
        titles = {track.title for track in albums[0].tracks}
        assert len(albums[0].tracks) == 2
        assert titles == {"01 Allegro.flac", "01 Andante.flac"}

    def test_they_share_one_cover_and_one_rating(self) -> None:
        """Which is the price: one handle is one cover and one rating."""
        albums, _ = assemble_albums(TWO_RECORDINGS)
        plain = AlbumIdentity(album_artist=COMPOSER, title=WORK, date=YEAR)
        assert albums[0].identity.handle == plain.handle
        assert albums[0].identity.art_key == plain.art_key
        assert album_handle(albums[0].identity) == album_handle(plain)
        assert track_handle(albums[0].identity, 1, 1) == track_handle(plain, 1, 1)

    def test_the_folding_is_the_same_on_every_scan(self) -> None:
        """Derived from the tags, so it cannot move between runs."""
        first, _ = assemble_albums(TWO_RECORDINGS)
        again, _ = assemble_albums(TWO_RECORDINGS)
        assert [album.identity.handle for album in first] == [
            album.identity.handle for album in again
        ]

    def test_folders_that_name_no_album_are_left_apart(self) -> None:
        """Folder names collide for reasons that say nothing about the music."""
        silent = tuple(
            SourceEntry(
                folder_name=WORK,
                parent_path=parent,
                parent_name=COMPOSER,
                candidate=one.candidate,
            )
            for parent, one in zip(
                ("H:/Music/Mahler/Abbado", "H:/Music/Mahler/Solti"), TWO_RECORDINGS
            )
        )
        albums, _ = assemble_albums(silent)
        assert len(albums) == 2


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
