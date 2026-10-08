"""Album identity and album structure."""

from __future__ import annotations

import pytest
from factories import make_track

from stellody.domain.album import Album, Disc
from stellody.domain.identity import ART_KEY_LENGTH, AlbumIdentity
from stellody.domain.track import TrackSource


def identity(**overrides: str) -> AlbumIdentity:
    """A valid identity with named fields overridden."""
    fields = {"album_artist": "Sasha", "title": "Involver", "date": "2004"}
    fields.update(overrides)
    return AlbumIdentity(**fields)


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"album_artist": ""}, "album artist"),
        ({"title": ""}, "a title"),
    ],
)
def test_invalid_identities_are_refused(
    overrides: dict[str, str], message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        identity(**overrides)


def test_identity_matches_across_tag_casing_and_full_dates() -> None:
    assert identity().key == identity(album_artist="SASHA", date="2004-05-01").key


def test_identity_without_a_date_still_has_a_key() -> None:
    assert identity(date="").key == ("sasha", "involver", "")


def test_sort_key_orders_by_artist_then_year_then_title() -> None:
    early = identity(title="The Qat Collection", date="1994")
    late = identity(title="Scene Delete", date="2016")
    undated = identity(title="Unknown", date="")
    assert sorted([late, early, undated], key=lambda i: i.sort_key) == [
        undated,
        early,
        late,
    ]


def test_sort_key_keeps_a_compilation_series_together_across_spellings() -> None:
    first = identity(album_artist="Various", title="Adapt", date="2019")
    second = identity(album_artist="Various Artists", title="Adapt #2", date="2016")
    tenth = identity(album_artist="VA", title="Adapt #10", date="2021")
    between = identity(album_artist="Various", title="Watergate 25", date="2018")
    earlier = identity(album_artist="Various Artists", title="Cream", date="2010")
    albums = [between, tenth, earlier, second, first]
    assert sorted(albums, key=lambda i: i.sort_key) == [
        first,
        second,
        tenth,
        earlier,
        between,
    ]


def test_sort_key_orders_one_compilation_title_by_year() -> None:
    later = identity(album_artist="Various", title="Hits", date="2020")
    sooner = identity(album_artist="Various Artists", title="Hits", date="1999")
    assert sorted([later, sooner], key=lambda i: i.sort_key) == [sooner, later]


def test_sort_key_compares_with_an_artist_that_only_sorts_like_a_compilation() -> None:
    person = identity(album_artist="The Various Artists", title="Debut", date="2001")
    compilation = identity(album_artist="Various", title="Adapt", date="2019")
    assert sorted([compilation, person], key=lambda i: i.sort_key)


def test_sort_key_numbers_a_series_by_value_within_a_year() -> None:
    titles = ["Adapt #10", "Adapt #2", "Adapt", "Adapt #3"]
    albums = [identity(title=title, date="2020") for title in titles]
    ordered = sorted(albums, key=lambda i: i.sort_key)
    assert [album.title for album in ordered] == [
        "Adapt",
        "Adapt #2",
        "Adapt #3",
        "Adapt #10",
    ]


def test_art_key_is_stable_and_short() -> None:
    key = identity().art_key
    assert key == identity(album_artist="sasha").art_key
    assert len(key) == ART_KEY_LENGTH
    assert key != identity(title="Invol2ver").art_key


def test_compilation_detection_and_display_fields() -> None:
    compilation = identity(album_artist="Various Artists", title="  Adapt  ")
    assert compilation.is_compilation is True
    assert compilation.display_title == "Adapt"
    assert compilation.display_artist == "Various Artists"
    assert identity().is_compilation is False


@pytest.mark.parametrize("spelling", ["Various", "VA", "Verschiedene"])
def test_every_compilation_spelling_is_shown_as_various_artists(
    spelling: str,
) -> None:
    compilation = identity(album_artist=spelling, title="Adapt")
    assert compilation.display_artist == "Various Artists"
    assert compilation.label == "Various Artists - Adapt"


def test_an_ordinary_artist_is_shown_as_tagged() -> None:
    assert identity(album_artist="  Sasha ").display_artist == "Sasha"


def test_a_disc_needs_a_positive_number() -> None:
    with pytest.raises(ValueError, match="disc numbers"):
        Disc(number=0, tracks=())


def test_disc_duration_sums_its_tracks() -> None:
    disc = Disc(
        number=1,
        tracks=(make_track(duration_ms=1000), make_track(duration_ms=2500)),
    )
    assert disc.duration_ms == 3500


def test_an_album_needs_at_least_one_track() -> None:
    with pytest.raises(ValueError, match="at least one track"):
        Album(identity=identity(), tracks=())


def _two_disc_album() -> Album:
    tracks = (
        make_track(disc_number=2, track_number=1, title="Fourth", artists=("B",)),
        make_track(disc_number=1, track_number=2, title="Second", artists=("A", "B")),
        make_track(disc_number=1, track_number=1, title="First", artists=("A",)),
    )
    return Album(identity=identity(), tracks=tracks, genre="House")


def test_discs_group_and_order_tracks() -> None:
    album = _two_disc_album()
    assert [disc.number for disc in album.discs] == [1, 2]
    assert [track.title for track in album.ordered_tracks()] == [
        "First",
        "Second",
        "Fourth",
    ]
    assert album.disc_count == 2
    assert album.track_count == 3


def test_album_totals_and_artist_order() -> None:
    album = _two_disc_album()
    assert album.duration_ms == 3000
    assert album.artists == ("A", "B")
    assert album.is_high_resolution is False


def test_high_resolution_album_is_detected() -> None:
    album = Album(identity=identity(), tracks=(make_track(sample_rate=96000),))
    assert album.is_high_resolution is True


def test_single_file_album_detection() -> None:
    shared = "album.flac"
    sliced = Album(
        identity=identity(),
        tracks=(
            make_track(source=TrackSource(shared, 0, 100), track_number=1),
            make_track(source=TrackSource(shared, 100, 200), track_number=2),
        ),
    )
    assert sliced.is_single_file is True


def test_multi_file_album_is_not_single_file() -> None:
    album = Album(
        identity=identity(),
        tracks=(
            make_track(source=TrackSource("a.flac"), track_number=1),
            make_track(source=TrackSource("b.flac"), track_number=2),
        ),
    )
    assert album.is_single_file is False


def test_one_whole_file_album_is_not_a_slice_album() -> None:
    album = Album(
        identity=identity(), tracks=(make_track(source=TrackSource("a.flac")),)
    )
    assert album.is_single_file is False
