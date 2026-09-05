"""Track sources and tracks, including the slice abstraction."""

from __future__ import annotations

import pytest
from factories import make_track

from stellody.domain.track import CD_SAMPLE_RATE, TrackSource, suffix_of


def test_a_whole_file_source_is_not_a_slice() -> None:
    source = TrackSource(path="album.flac")
    assert source.is_slice is False
    assert source.frame_count is None
    assert source.duration_ms(CD_SAMPLE_RATE) is None


def test_a_cue_source_is_a_slice_with_a_known_length() -> None:
    source = TrackSource(path="album.flac", start_frame=44100, end_frame=132300)
    assert source.is_slice is True
    assert source.frame_count == 88200
    assert source.duration_ms(CD_SAMPLE_RATE) == 2000


def test_a_source_starting_late_but_running_to_the_end_is_a_slice() -> None:
    source = TrackSource(path="album.flac", start_frame=44100)
    assert source.is_slice is True
    assert source.frame_count is None


def test_duration_needs_a_positive_sample_rate() -> None:
    source = TrackSource(path="a.flac", start_frame=0, end_frame=100)
    assert source.duration_ms(0) is None


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"path": ""}, "needs a path"),
        ({"path": "a.flac", "start_frame": -1}, "cannot be negative"),
        ({"path": "a.flac", "start_frame": 10, "end_frame": 10}, "beyond"),
        ({"path": "a.flac", "start_frame": 10, "end_frame": 5}, "beyond"),
    ],
)
def test_invalid_sources_are_refused(kwargs: dict[str, object], message: str) -> None:
    with pytest.raises(ValueError, match=message):
        TrackSource(**kwargs)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"disc_number": 0}, "disc numbers"),
        ({"track_number": 0}, "track numbers"),
        ({"title": ""}, "needs a title"),
        ({"artists": ()}, "at least one artist"),
        ({"duration_ms": -1}, "duration cannot"),
        ({"sample_rate": 0}, "sample rate"),
        ({"bit_depth": -1}, "bit depth"),
    ],
)
def test_invalid_tracks_are_refused(overrides: dict[str, object], message: str) -> None:
    with pytest.raises(ValueError, match=message):
        make_track(**overrides)


def test_ordering_key_places_a_track_within_its_album() -> None:
    track = make_track(disc_number=2, track_number=3, title="The Ending")
    assert track.ordering_key == (2, 3, "ending")


def test_artist_text_joins_every_credited_artist() -> None:
    track = make_track(artists=("Chicane", "Bryan Adams"))
    assert track.artist_text == "Chicane, Bryan Adams"


@pytest.mark.parametrize(
    ("rate", "depth", "expected"),
    [
        (44100, 16, False),
        (96000, 16, True),
        (44100, 24, True),
        (192000, 24, True),
        # A file stating no depth cannot make the claim. The second is Opus,
        # which always decodes at 48 kHz whatever it was encoded from, so a
        # rate test alone would badge every Opus file better than CD.
        (44100, 0, False),
        (48000, 0, False),
    ],
)
def test_high_resolution_detection(rate: int, depth: int, expected: bool) -> None:
    assert make_track(sample_rate=rate, bit_depth=depth).is_high_resolution is expected


def test_a_track_may_state_no_bit_depth() -> None:
    """A lossy source reports nought, which is the absence of a reading."""
    track = make_track(bit_depth=0)
    assert track.bit_depth == 0
    assert track.states_depth is False


def test_a_stated_depth_says_so() -> None:
    assert make_track(bit_depth=16).states_depth is True


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        ("H:/Album/12 Bonkers.m4v", ".m4v"),
        (r"H:\Album\12 Bonkers.M4V", ".m4v"),
        ("track.flac", ".flac"),
        ("H:/An.Album.Named.So/track", ""),
        ("H:/Album/.flac", ""),
        ("plain", ""),
    ],
)
def test_suffix_of_reads_the_name_rather_than_the_path(
    path: str, expected: str
) -> None:
    assert suffix_of(path) == expected


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        ("H:/Album/12 Bonkers.m4v", True),
        (r"H:\Album\12 Bonkers.M4V", True),
        ("H:/Album/12 Bonkers.flac", False),
        ("H:/Album/12 Bonkers.m4a", False),
        ("H:/Video.m4v/12 Bonkers.flac", False),
    ],
)
def test_a_source_says_whether_it_carries_a_picture(path: str, expected: bool) -> None:
    assert TrackSource(path=path).carries_picture is expected


def test_a_picture_bearing_source_is_still_an_ordinary_slice() -> None:
    """Carrying a picture changes what is shown, never how the sound is cut."""
    source = TrackSource(path="bonus.m4v", start_frame=48000, end_frame=96000)
    assert source.carries_picture is True
    assert source.is_slice is True
    assert source.frame_count == 48000
