"""One album in several folders is one album.

Three shapes measured on the reference library, each of which showed as two or
more tiles carrying one name and one cover, with nothing to tell them apart:

  * an album's audio under Compilations while its bonus videos sat under the
    artist, both tagged alike, dated a year apart
  * the same, where the two folders happen to agree about the year
  * nine single folders under one artist, each holding one track, every one
    tagged with the same album name

The cost of folding them is that two recordings of one work, tagged alike, are
now one album; that is held in `test_identity_collisions` rather than here.
"""

from __future__ import annotations

from stellody.domain.grouping import SourceEntry, assemble_albums
from stellody.domain.ordering import TrackCandidate
from stellody.domain.track import TrackSource

RATE = 44100


def entry(
    parent: str,
    folder: str,
    name: str,
    *,
    track: int,
    album: str,
    artist: str,
    date: str = "",
) -> SourceEntry:
    """One source, tagged as the real files are."""
    return SourceEntry(
        folder_name=folder,
        parent_path=parent,
        parent_name=parent.rsplit("/", 1)[-1],
        candidate=TrackCandidate(
            file_name=name,
            source=TrackSource(path=f"{parent}/{folder}/{name}"),
            duration_ms=200_000,
            sample_rate=RATE,
            bit_depth=16,
            tag_track=track,
            tag_title=name,
            artists=(artist,),
        ),
        album=album,
        album_artist=artist,
        date=date,
    )


class TestAnAlbumSplitAcrossTwoFolders:
    """Florence, whose audio and video folders are dated a year apart."""

    ENTRIES = (
        entry(
            "H:/FLACMusic/Compilations",
            "Lungs",
            "01 Dog Days Are Over.m4a",
            track=1,
            album="Lungs",
            artist="Florence + the Machine",
            date="2008-12-01T08:00:00Z",
        ),
        entry(
            "H:/FLACMusic/Florence + the Machine",
            "Lungs",
            "15 Dog Days Are Over.m4v",
            track=15,
            album="Lungs",
            artist="Florence + the Machine",
            date="2009-01-01T08:00:00Z",
        ),
    )

    def test_the_two_folders_are_one_album(self) -> None:
        albums, _ = assemble_albums(self.ENTRIES)
        assert len(albums) == 1

    def test_a_year_apart_does_not_keep_them_apart(self) -> None:
        """The date is left out of what folds, measured against these files."""
        albums, _ = assemble_albums(self.ENTRIES)
        assert albums[0].track_count == 2

    def test_the_video_track_keeps_its_number(self) -> None:
        albums, _ = assemble_albums(self.ENTRIES)
        assert [track.track_number for track in albums[0].tracks] == [1, 15]


class TestNineSinglesTaggedAsOneAlbum:
    """Shaun Ansari: nine folders, one track each, all tagged the same album."""

    ENTRIES = tuple(
        entry(
            "H:/FLACMusic/Shaun Ansari",
            folder,
            "01 Track.flac",
            track=1,
            album="Shaun Ansari",
            artist="Shaun Ansari",
        )
        for folder in (
            "Fury - Single",
            "Indigo - EP",
            "Karachi - Single",
            "Miracle - Single",
            "Sparkles",
        )
    )

    def test_they_are_one_album(self) -> None:
        albums, _ = assemble_albums(self.ENTRIES)
        assert len(albums) == 1

    def test_every_track_is_kept(self) -> None:
        """None is dropped as a duplicate: they are different songs."""
        albums, _ = assemble_albums(self.ENTRIES)
        assert albums[0].track_count == len(self.ENTRIES)

    def test_the_clashing_track_numbers_are_reported(self) -> None:
        """Every one of them claims track 1, which is the tags being wrong."""
        _albums, issues = assemble_albums(self.ENTRIES)
        assert issues


class TestWhatIsNotFolded:
    def test_folders_naming_no_album_stay_apart(self) -> None:
        """A folder name says nothing: two parents can each hold one called Live."""
        entries = tuple(
            SourceEntry(
                folder_name="Live",
                parent_path=parent,
                parent_name="Someone",
                candidate=TrackCandidate(
                    file_name="01 One.flac",
                    source=TrackSource(path=f"{parent}/Live/01 One.flac"),
                    duration_ms=1000,
                    sample_rate=RATE,
                    bit_depth=16,
                    tag_track=1,
                    tag_title="One",
                    artists=(),
                ),
            )
            for parent in ("H:/FLACMusic/A", "H:/FLACMusic/B")
        )
        albums, _ = assemble_albums(entries)
        assert len(albums) == 2

    def test_an_album_naming_no_artist_stays_apart(self) -> None:
        """Half a name is not a name; both halves have to agree to fold."""
        entries = tuple(
            entry(
                parent,
                "Lungs",
                "01 One.flac",
                track=1,
                album="Lungs",
                artist="",
            )
            for parent in ("H:/FLACMusic/A", "H:/FLACMusic/B")
        )
        albums, _ = assemble_albums(entries)
        assert len(albums) == 2

    def test_different_albums_by_one_artist_stay_apart(self) -> None:
        entries = (
            entry(
                "H:/FLACMusic/Dizzee Rascal",
                "Showtime",
                "01 One.flac",
                track=1,
                album="Showtime",
                artist="Dizzee Rascal",
            ),
            entry(
                "H:/FLACMusic/Dizzee Rascal",
                "Boy In da Corner",
                "01 Two.flac",
                track=1,
                album="Boy In da Corner",
                artist="Dizzee Rascal",
            ),
        )
        albums, _ = assemble_albums(entries)
        assert len(albums) == 2
