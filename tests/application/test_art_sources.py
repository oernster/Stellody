"""Gathering an album's cover candidates, then asking for them in two stages.

An album can span several folders, so the candidates are gathered across all
of them. A cue-sheet album is the opposite case: many tracks sharing one file,
which must be offered once rather than once per track.
"""

from __future__ import annotations

import os

import pytest

from stellody.application.artwork import AlbumArt, AlbumArtSources, sources_for
from stellody.application.ports import FolderRecord
from stellody.domain.album import Album
from stellody.domain.identity import AlbumIdentity
from stellody.domain.track import CD_SAMPLE_RATE, Track, TrackSource

FIRST = os.path.join("Music", "Holst")
SECOND = os.path.join("Music", "Holst CD2")


def _track(folder: str, name: str, number: int = 1, start: int = 0) -> Track:
    """One track living in a named folder."""
    return Track(
        source=TrackSource(path=os.path.join(folder, name), start_frame=start),
        disc_number=1,
        track_number=number,
        title=f"Track {number}",
        artists=("Holst",),
        duration_ms=1000,
        sample_rate=CD_SAMPLE_RATE,
        bit_depth=16,
    )


def _album(*tracks: Track, title: str = "The Planets") -> Album:
    """An album holding these tracks."""
    return Album(
        identity=AlbumIdentity(album_artist="Holst", title=title), tracks=tracks
    )


def _record(folder: str, art: str = "", embedded: bool = False) -> FolderRecord:
    """What the scan recorded about one folder."""
    return FolderRecord(folder=folder, art_path=art, has_embedded_art=embedded)


class _Artwork:
    """The artwork port, stood in for. It records what it was asked."""

    def __init__(self, kept: bytes | None = None, read_back: bytes | None = None):
        self.kept = kept
        self.read_back = read_back
        self.asked: list[tuple[str, tuple[str, ...], tuple[str, ...]]] = []

    def remembered(self, key: str) -> bytes | None:
        """The cover already kept, if any."""
        return self.kept

    def read(self, key, sidecars, audio) -> bytes | None:
        """Record the ask, then answer."""
        self.asked.append((key, sidecars, audio))
        return self.read_back


class TestGatheringCandidates:
    def test_a_file_beside_the_music_is_offered(self) -> None:
        cover = os.path.join(FIRST, "cover.jpg")
        album = _album(_track(FIRST, "01.flac"))
        (found,) = sources_for((album,), (_record(FIRST, art=cover),))
        assert found.sidecars == (cover,)
        assert found.audio == ()

    def test_a_picture_inside_the_audio_is_offered(self) -> None:
        album = _album(_track(FIRST, "01.flac"), _track(FIRST, "02.flac", 2))
        (found,) = sources_for((album,), (_record(FIRST, embedded=True),))
        assert found.sidecars == ()
        assert found.audio == (
            os.path.join(FIRST, "01.flac"),
            os.path.join(FIRST, "02.flac"),
        )

    def test_a_folder_with_neither_offers_nothing(self) -> None:
        album = _album(_track(FIRST, "01.flac"))
        (found,) = sources_for((album,), (_record(FIRST),))
        assert found.is_empty

    def test_a_cue_album_offers_its_one_file_once(self) -> None:
        """Many tracks share the file, so opening it once is the point."""
        whole = "album.flac"
        album = _album(
            _track(FIRST, whole, 1, start=0),
            _track(FIRST, whole, 2, start=100),
            _track(FIRST, whole, 3, start=200),
        )
        (found,) = sources_for((album,), (_record(FIRST, embedded=True),))
        assert found.audio == (os.path.join(FIRST, whole),)

    def test_an_album_spanning_two_folders_gathers_both(self) -> None:
        """Sibling disc folders merge into one album, so both are candidates."""
        first_cover = os.path.join(FIRST, "cover.jpg")
        second_cover = os.path.join(SECOND, "folder.jpg")
        album = _album(_track(FIRST, "01.flac"), _track(SECOND, "01.flac", 2))
        (found,) = sources_for(
            (album,),
            (_record(FIRST, art=first_cover), _record(SECOND, art=second_cover)),
        )
        assert found.sidecars == (first_cover, second_cover)

    def test_a_folder_seen_twice_offers_its_cover_once(self) -> None:
        cover = os.path.join(FIRST, "cover.jpg")
        album = _album(_track(FIRST, "01.flac"), _track(FIRST, "02.flac", 2))
        (found,) = sources_for((album,), (_record(FIRST, art=cover),))
        assert found.sidecars == (cover,)

    def test_a_track_whose_folder_was_never_recorded_is_passed_over(self) -> None:
        """A record can be missing; it must not take the whole album down."""
        cover = os.path.join(FIRST, "cover.jpg")
        album = _album(_track(FIRST, "01.flac"), _track(SECOND, "01.flac", 2))
        (found,) = sources_for((album,), (_record(FIRST, art=cover),))
        assert found.sidecars == (cover,)

    def test_each_album_gets_its_own_entry(self) -> None:
        first = _album(_track(FIRST, "01.flac"), title="The Planets")
        second = _album(_track(SECOND, "01.flac"), title="Egdon Heath")
        gathered = sources_for((first, second), (_record(FIRST), _record(SECOND)))
        assert len(gathered) == 2
        assert gathered[0].key != gathered[1].key

    def test_the_key_is_the_album_identity_handle(self) -> None:
        album = _album(_track(FIRST, "01.flac"))
        (found,) = sources_for((album,), (_record(FIRST),))
        assert found.key == album.identity.art_key


class TestSources:
    def test_sources_need_an_album_to_belong_to(self) -> None:
        with pytest.raises(ValueError):
            AlbumArtSources(key="")

    def test_somewhere_to_look_is_not_empty(self) -> None:
        assert not AlbumArtSources(key="k", sidecars=("a.jpg",)).is_empty
        assert not AlbumArtSources(key="k", audio=("a.flac",)).is_empty
        assert AlbumArtSources(key="k").is_empty


class TestAsking:
    def test_a_kept_cover_comes_back_without_reading(self) -> None:
        artwork = _Artwork(kept=b"kept")
        assert AlbumArt(artwork).remembered(AlbumArtSources(key="k")) == b"kept"
        assert artwork.asked == []

    def test_reading_asks_for_every_candidate_in_order(self) -> None:
        artwork = _Artwork(read_back=b"read")
        sources = AlbumArtSources(key="k", sidecars=("a.jpg",), audio=("b.flac",))
        assert AlbumArt(artwork).reading(sources) == b"read"
        assert artwork.asked == [("k", ("a.jpg",), ("b.flac",))]

    def test_an_album_with_nowhere_to_look_is_never_read(self) -> None:
        """Opening nothing is cheaper than asking a decoder to open nothing."""
        artwork = _Artwork(read_back=b"read")
        assert AlbumArt(artwork).reading(AlbumArtSources(key="k")) is None
        assert artwork.asked == []
