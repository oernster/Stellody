"""Offering an album some cover art, then keeping the one that was chosen.

Hand-written fakes rather than a mock library. No connection is opened
here: the port is a Protocol, so standing in front of it needs nothing but a
class with the right two methods.
"""

from __future__ import annotations

import pytest

from stellody.application.choosing_covers import ChooseCover
from stellody.domain.cover_choice import CoverCandidate, CoverOffer
from stellody.domain.identity import AlbumIdentity

FULL = "https://coverartarchive.org/release/abc/1.jpg"
SMALL = "https://coverartarchive.org/release/abc/1-250.jpg"


def candidate(**overrides: object) -> CoverCandidate:
    """One candidate, with the fields a given test cares about."""
    fields: dict[str, object] = {
        "release": "Ether Song",
        "image_url": FULL,
        "thumbnail_url": SMALL,
    }
    fields.update(overrides)
    return CoverCandidate(**fields)  # type: ignore[arg-type]


class RecordingSearch:
    """A search that answers what it was told to and remembers being asked."""

    def __init__(self, offered=(), pictures=None, refused=False) -> None:
        self.offered = tuple(offered)
        self.refused = refused
        self.pictures = pictures if pictures is not None else {}
        self.searched: list[tuple[str, str]] = []
        self.fetched: list[str] = []

    def search(self, artist: str, album: str) -> CoverOffer:
        """Answer the canned offer, noting what was asked for."""
        self.searched.append((artist, album))
        return CoverOffer(self.offered, refused=self.refused)

    def fetch(self, url: str):
        """The canned bytes for that address; None when there are none."""
        self.fetched.append(url)
        return self.pictures.get(url)


class RecordingArtwork:
    """An artwork store that keeps what it is given, in memory."""

    def __init__(self, refuses: bool = False) -> None:
        self.refuses = refuses
        self.kept: dict[str, bytes] = {}

    def remembered(self, key: str):
        """Whatever is kept for that album."""
        return self.kept.get(key)

    def read(self, key: str, sidecars, audio):
        """Never asked for here: a chosen cover is preferred to a read one."""

    def keep_chosen(self, key: str, data: bytes):
        """Keep it, unless this store is standing in for one that cannot."""
        if self.refuses:
            return None
        self.kept[key] = data
        return data


IDENTITY = AlbumIdentity(album_artist="Turin Brakes", title="Ether Song")


class TestWhatIsOffered:
    def test_the_album_is_looked_up_by_artist_and_title(self) -> None:
        search = RecordingSearch(offered=(candidate(),))
        ChooseCover(search, RecordingArtwork()).offer(IDENTITY)
        assert search.searched == [("Turin Brakes", "Ether Song")]

    def test_what_comes_back_is_put_in_order(self) -> None:
        back = candidate(release="back", largest_px=1200, is_front=False)
        front = candidate(release="front", largest_px=250, is_front=True)
        search = RecordingSearch(offered=(back, front))
        offered = ChooseCover(search, RecordingArtwork()).offer(IDENTITY)
        assert [one.release for one in offered.candidates] == ["front", "back"]

    def test_a_lookup_that_finds_nothing_offers_nothing(self) -> None:
        offered = ChooseCover(RecordingSearch(), RecordingArtwork()).offer(IDENTITY)
        assert offered == CoverOffer()
        assert not offered.refused

    def test_a_refusal_is_carried_through_rather_than_flattened(self) -> None:
        """An album nobody was asked about is not an album with no art.

        The service is the last place that could tell the two apart, so a
        refusal travelling as an empty offer would be indistinguishable from an
        answer by the time anything drew it.
        """
        search = RecordingSearch(refused=True)
        offered = ChooseCover(search, RecordingArtwork()).offer(IDENTITY)
        assert offered.refused
        assert offered.is_empty

    def test_an_answered_search_is_never_marked_refused(self) -> None:
        search = RecordingSearch(offered=(candidate(),))
        offered = ChooseCover(search, RecordingArtwork()).offer(IDENTITY)
        assert not offered.refused
        assert not offered.is_empty

    def test_an_identity_always_carries_both_names(self) -> None:
        """Which is why nothing here guards against an album missing one."""
        with pytest.raises(ValueError):
            AlbumIdentity(album_artist="", title="Ether Song")
        with pytest.raises(ValueError):
            AlbumIdentity(album_artist="Turin Brakes", title="")


class TestAcceptingOne:
    def test_the_chosen_picture_is_fetched_and_kept(self) -> None:
        search = RecordingSearch(pictures={FULL: b"a picture"})
        artwork = RecordingArtwork()
        kept = ChooseCover(search, artwork).accept("thekey", candidate())
        assert kept == b"a picture"
        assert artwork.kept == {"thekey": b"a picture"}
        assert search.fetched == [FULL], "the full picture, not the thumbnail"

    def test_a_fetch_that_fails_keeps_nothing(self) -> None:
        artwork = RecordingArtwork()
        assert ChooseCover(RecordingSearch(), artwork).accept("k", candidate()) is None
        assert artwork.kept == {}

    def test_an_empty_answer_is_not_kept_as_a_cover(self) -> None:
        """Zero bytes are not a picture; a record pointing at them is worse."""
        search = RecordingSearch(pictures={FULL: b""})
        artwork = RecordingArtwork()
        assert ChooseCover(search, artwork).accept("k", candidate()) is None
        assert artwork.kept == {}

    def test_a_store_that_cannot_keep_it_says_so(self) -> None:
        search = RecordingSearch(pictures={FULL: b"a picture"})
        chooser = ChooseCover(search, RecordingArtwork(refuses=True))
        assert chooser.accept("k", candidate()) is None


class TestThePreviewTheChooserDraws:
    def test_it_asks_for_the_thumbnail_rather_than_the_picture(self) -> None:
        """A dozen full pictures is a chooser nobody waits for."""
        search = RecordingSearch(pictures={SMALL: b"small"})
        assert ChooseCover(search, RecordingArtwork()).preview(candidate()) == b"small"
        assert search.fetched == [SMALL]

    def test_a_thumbnail_that_cannot_be_had_draws_nothing(self) -> None:
        chooser = ChooseCover(RecordingSearch(), RecordingArtwork())
        assert chooser.preview(candidate()) is None
