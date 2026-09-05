"""A lossy copy of an album already held lossless is one album, not two.

Reported from a real library; it did real damage. Until M4A could be
decoded a second lossy rip was invisible; the moment it was not, three albums
that had sat in the library for its whole life were reported as no longer
found. Nothing had been deleted and nothing renamed: the lossy copy collided
with the lossless one, so BOTH were told apart by where they were found; the
album that was already there had its handle moved. A moved handle is a
cover, an album rating and every track rating under it that can no longer be
looked up.

One rule answers it now, in one place. Folders naming the same album are one
album, so both rips land in one group, where a lossy file is dropped exactly
where a lossless file is that same track. The album then keeps the handle it
always had, because nothing collides with it any more: there is one album where
there were two.
"""

from __future__ import annotations

from stellody.domain.grouping import SourceEntry, assemble_albums
from stellody.domain.ordering import TrackCandidate
from stellody.domain.track import TrackSource

RATE = 44100
ARTIST = "Fleetwood Mac"
ALBUM = "The Dance"
YEAR = "1997"

# Long enough that a two second tolerance is a small part of it.
DEFAULT_MS = 300_000

LOSSLESS_DEPTH = 16
# What the probe reports for a file whose format states no depth. It is the
# library's existing signal for a lossy source, not a new one invented here.
LOSSY_DEPTH = 0


def entry(
    parent: str,
    name: str,
    *,
    depth: int,
    track: int | None,
    disc: int | None = None,
    length: int = DEFAULT_MS,
    title: str = "",
    date: str = YEAR,
    album: str = ALBUM,
) -> SourceEntry:
    """One source in an album folder."""
    return SourceEntry(
        folder_name=album,
        parent_path=parent,
        parent_name=ARTIST,
        candidate=TrackCandidate(
            file_name=name,
            source=TrackSource(path=f"{parent}/{album}/{name}"),
            duration_ms=length,
            sample_rate=RATE,
            bit_depth=depth,
            tag_disc=disc,
            tag_track=track,
            tag_title=title or name,
            artists=(ARTIST,),
        ),
        album=album,
        album_artist=ARTIST,
        date=date,
    )


HERE = "H:/FLACMusic/Fleetwood Mac"
THERE = "H:/FLACMusic/Fleetwood Mac Again"


def _only(entries: tuple[SourceEntry, ...]):
    albums, _ = assemble_albums(entries)
    assert len(albums) == 1, f"expected one album, got {len(albums)}"
    return albums[0]


class TestOneFolderHoldingBothRips:
    """The Dance: 17 FLAC and 17 M4A of one performance, paired by number."""

    BOTH = (
        entry(HERE, "01 The Chain.flac", depth=LOSSLESS_DEPTH, track=1),
        entry(HERE, "01 The Chain (Live).m4a", depth=LOSSY_DEPTH, track=1),
        entry(HERE, "02 Dreams.flac", depth=LOSSLESS_DEPTH, track=2),
        entry(HERE, "02 Dreams (Live).m4a", depth=LOSSY_DEPTH, track=2),
    )

    def test_each_track_appears_once(self) -> None:
        """Not twice, which is what a listener saw."""
        assert _only(self.BOTH).track_count == 2

    def test_the_lossless_file_is_the_one_kept(self) -> None:
        kept = {track.source.path for track in _only(self.BOTH).tracks}
        assert all(path.endswith(".flac") for path in kept), kept

    def test_the_titles_are_the_lossless_ones(self) -> None:
        """The lossy rip suffixes every title, so this says which won."""
        titles = {track.title for track in _only(self.BOTH).tracks}
        assert not any("(Live)" in title for title in titles), titles

    def test_the_album_still_states_a_depth(self) -> None:
        """A dropped lossy file must not leave the album looking lossy."""
        assert all(track.states_depth for track in _only(self.BOTH).tracks)


class TestWhatIsNeverDropped:
    def test_a_lossy_track_the_lossless_rip_does_not_have_is_kept(self) -> None:
        """A bonus track only the lossy rip carries is music, not a duplicate."""
        entries = (
            entry(HERE, "01 The Chain.flac", depth=LOSSLESS_DEPTH, track=1),
            entry(HERE, "02 Bonus.m4a", depth=LOSSY_DEPTH, track=2),
        )
        assert _only(entries).track_count == 2

    def test_a_file_with_no_track_number_is_kept(self) -> None:
        """The Bends: two untagged WAVs beside one numbered M4A.

        Nothing pairs with an unnumbered file, so a rule about duplicates must
        not reach it. Dropping either would have lost a recording outright.
        """
        entries = (
            entry(HERE, "one.wav", depth=LOSSLESS_DEPTH, track=None),
            entry(HERE, "two.wav", depth=LOSSLESS_DEPTH, track=None),
            entry(HERE, "03 High and Dry.m4a", depth=LOSSY_DEPTH, track=3),
        )
        assert _only(entries).track_count == 3

    def test_a_folder_of_only_lossy_files_is_untouched(self) -> None:
        """With nothing lossless to prefer, every file is the only copy there is."""
        entries = (
            entry(HERE, "01 One.m4a", depth=LOSSY_DEPTH, track=1),
            entry(HERE, "02 Two.m4a", depth=LOSSY_DEPTH, track=2),
        )
        assert _only(entries).track_count == 2

    def test_the_same_number_on_another_disc_is_a_different_track(self) -> None:
        entries = (
            entry(HERE, "01 One.flac", depth=LOSSLESS_DEPTH, track=1, disc=1),
            entry(HERE, "01 Other.m4a", depth=LOSSY_DEPTH, track=1, disc=2),
        )
        assert _only(entries).track_count == 2


class TestAVariantIsNotACopy:
    """A number alone cannot say two files hold the same performance.

    Raised against the first version of this rule, which dropped a file purely
    because a lossless file shared its track number. An album may hold a studio
    take and a live one at one number; the lossy rip of The Dance titling every
    track "(Live)" is exactly the shape that should make anyone check. Lengths
    are what settled it there; lengths are what the rule now requires.
    """

    def test_a_track_of_a_different_length_is_kept(self) -> None:
        """Two takes of one song, not one take twice."""
        entries = (
            entry(HERE, "05 Studio.flac", depth=LOSSLESS_DEPTH, track=5),
            entry(HERE, "05 Live.m4a", depth=LOSSY_DEPTH, track=5, length=402_000),
        )
        assert _only(entries).track_count == 2

    def test_a_track_of_the_same_length_is_dropped(self) -> None:
        """The Dance: every pair agreed to within 0.7 of a second."""
        entries = (
            entry(HERE, "01 The Chain.flac", depth=LOSSLESS_DEPTH, track=1),
            entry(
                HERE,
                "01 The Chain (Live).m4a",
                depth=LOSSY_DEPTH,
                track=1,
                length=DEFAULT_MS - 700,
            ),
        )
        assert _only(entries).track_count == 1

    def test_the_survivor_is_the_lossless_one(self) -> None:
        entries = (
            entry(HERE, "01 One.flac", depth=LOSSLESS_DEPTH, track=1),
            entry(HERE, "01 One.m4a", depth=LOSSY_DEPTH, track=1, length=DEFAULT_MS),
        )
        assert _only(entries).tracks[0].source.path.endswith(".flac")


class TestPairingWhenOnlyOneRipStatesADisc:
    """Measured: the FLAC rip states no disc number and the M4A states disc 1."""

    MISMATCHED = (
        entry(HERE, "01 The Chain.flac", depth=LOSSLESS_DEPTH, track=1, disc=None),
        entry(HERE, "01 The Chain (Live).m4a", depth=LOSSY_DEPTH, track=1, disc=1),
    )

    def test_they_are_still_recognised_as_one_track(self) -> None:
        """Compared as written they missed; the album listed everything twice."""
        assert _only(self.MISMATCHED).track_count == 1

    def test_the_lossless_one_is_the_survivor(self) -> None:
        kept = _only(self.MISMATCHED).tracks[0]
        assert kept.source.path.endswith(".flac")

    def test_it_reads_the_same_way_round(self) -> None:
        """The lossless file stating the disc and the lossy one silent on it."""
        entries = (
            entry(HERE, "01 One.flac", depth=LOSSLESS_DEPTH, track=1, disc=1),
            entry(HERE, "01 One.m4a", depth=LOSSY_DEPTH, track=1, disc=None),
        )
        assert _only(entries).track_count == 1


class TestTwoFoldersHoldingTheSameAlbum:
    """Led Zeppelin, This Is War and Immersion: a lossless rip and a lossy one."""

    LOSSLESS = (entry(HERE, "01 One.flac", depth=LOSSLESS_DEPTH, track=1),)
    BOTH = LOSSLESS + (entry(THERE, "01 One.m4a", depth=LOSSY_DEPTH, track=1),)

    def test_the_two_folders_fold_into_one_album(self) -> None:
        """Folders that name one album are one album, wherever they sit."""
        albums, _ = assemble_albums(self.BOTH)
        assert len(albums) == 1

    def test_the_lossy_copy_is_then_dropped_as_the_duplicate_it_is(self) -> None:
        """Folding brings the two copies together, where this rule can see them.

        Apart, they were two albums and each kept its own tracks. Together they
        are one album holding one copy of each track, which is the lossless
        one, since a lossy file of a track already held lossless is the same
        recording again rather than another track.
        """
        album = _only(self.BOTH)
        assert album.track_count == 1
        assert album.tracks[0].source.path.endswith(".flac")

    def test_the_lossless_copy_keeps_the_handle_it_had_alone(self) -> None:
        """THE regression. Its cover and every rating are looked up by this.

        Measured against the same album with nothing colliding with it, which
        is what the library held before the lossy copy became visible.
        """
        alone, _ = assemble_albums(self.LOSSLESS)
        together, _ = assemble_albums(self.BOTH)
        lossless = [
            album for album in together if album.tracks[0].source.path.endswith(".flac")
        ]
        assert len(lossless) == 1
        assert lossless[0].identity.handle == alone[0].identity.handle

    def test_the_album_carries_no_discriminator(self) -> None:
        """Nothing collides with it any more, because nothing is beside it."""
        assert _only(self.BOTH).identity.discriminator == ""


class TestWhatMustNotChange:
    """The case the telling apart was written for, left exactly as it was."""

    def test_two_lossless_recordings_fold_into_one_album(self) -> None:
        """A symphony under two conductors: the price of folding.

        Neither is a copy of the other, so neither is dropped: the album holds
        both. What is given up is that they are one album rather than two, so
        they share a cover and a rating. The owner chose that, against the three
        real libraries where one album genuinely sat in two folders.
        """
        entries = (
            entry(HERE, "01 Allegro.flac", depth=LOSSLESS_DEPTH, track=1),
            entry(THERE, "01 Andante.flac", depth=LOSSLESS_DEPTH, track=1),
        )
        album = _only(entries)
        assert album.track_count == 2
        assert album.identity.discriminator == ""

    def test_two_lossy_copies_fold_and_both_are_kept(self) -> None:
        """With none lossless there is no copy to prefer, so neither is dropped.

        The same rule as a single folder holding only lossy files: dropping one
        needs a lossless file to say which is the copy; there is none here.
        """
        entries = (
            entry(HERE, "01 One.m4a", depth=LOSSY_DEPTH, track=1),
            entry(THERE, "01 One.m4a", depth=LOSSY_DEPTH, track=1),
        )
        assert _only(entries).track_count == 2

    def test_an_album_nothing_collides_with_keeps_a_plain_handle(self) -> None:
        entries = (entry(HERE, "01 One.flac", depth=LOSSLESS_DEPTH, track=1),)
        albums, _ = assemble_albums(entries)
        assert albums[0].identity.discriminator == ""
