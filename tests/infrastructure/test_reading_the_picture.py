"""The picture stream, walked forward by the moment the sound has reached.

Driven by files whose frames name themselves: each picture in the fixture is a
flat grey stepping one value per frame, so the frame a reader hands back can be
identified by reading a single pixel rather than by trusting a timestamp. That
is what makes "the right frame" an assertion rather than an impression.

The tolerance below is for the codec, not for the reader. A flat grey survives
H.264 almost exactly; measured across the frames asserted here, the largest
difference between the value encoded and the value decoded was 1.
"""

from __future__ import annotations

import pathlib

import pytest
from video_support import FRAMES_PER_SECOND, grey_for, write_m4v

from stellody.domain.picture import BYTES_PER_PIXEL
from stellody.domain.track import TrackSource
from stellody.infrastructure.video import PictureError, VideoReader

RATE = 44100
SECONDS = 3
FRAMES = RATE * SECONDS
GREY_TOLERANCE = 2
# Half way into a frame's own time, so a reading is never taken on the join.
HALF_A_FRAME_MS = 1000 // FRAMES_PER_SECOND // 2


def moment_of(picture_number: int) -> int:
    """Part way through the time that frame is the one showing."""
    return picture_number * 1000 // FRAMES_PER_SECOND + HALF_A_FRAME_MS


@pytest.fixture(scope="module")
def bonus(tmp_path_factory: pytest.TempPathFactory) -> pathlib.Path:
    """One video, encoded once for the whole module."""
    folder = tmp_path_factory.mktemp("picture")
    return write_m4v(folder / "12 Bonus.m4v", frames=FRAMES)


@pytest.fixture
def reader(bonus: pathlib.Path):
    """A reader over that video, closed however the test ends."""
    made = VideoReader(TrackSource(path=str(bonus)))
    yield made
    made.close()


def shown(reader, at_ms: int) -> int:
    """The grey of the frame the reader says is showing then."""
    picture = reader.picture_at(at_ms)
    assert picture is not None
    return picture.data[0]


class TestWhatItHandsBack:
    def test_it_states_the_size_the_file_holds(self, reader) -> None:
        picture = reader.picture_at(0)
        assert reader.size == (picture.width, picture.height)

    def test_a_picture_carries_three_bytes_a_pixel(self, reader) -> None:
        picture = reader.picture_at(0)
        assert len(picture.data) == picture.width * picture.height * BYTES_PER_PIXEL
        assert picture.bytes_per_row == picture.width * BYTES_PER_PIXEL


class TestTheRightFrame:
    @pytest.mark.parametrize("number", [0, 1, 2, 5, 10, 24, 40, 60, 74])
    def test_it_shows_the_frame_due_at_that_moment(self, reader, number) -> None:
        """Not the one after it, which is the fault this was written against."""
        assert abs(shown(reader, moment_of(number)) - grey_for(number)) <= (
            GREY_TOLERANCE
        )

    def test_a_frame_shows_until_the_next_one_is_due(self, reader) -> None:
        """A moment later in the same frame's time is the same picture."""
        early = shown(reader, moment_of(10) - HALF_A_FRAME_MS + 1)
        late = shown(reader, moment_of(10) + HALF_A_FRAME_MS - 1)
        assert early == late

    def test_asking_for_the_same_moment_twice_gives_the_same_frame(
        self, reader
    ) -> None:
        assert shown(reader, moment_of(12)) == shown(reader, moment_of(12))


class TestMovingAbout:
    def test_going_backwards_finds_the_earlier_frame(self, reader) -> None:
        """A listener seeking back is not walked forward to the end."""
        shown(reader, moment_of(60))
        assert abs(shown(reader, moment_of(5)) - grey_for(5)) <= GREY_TOLERANCE

    def test_a_long_jump_forward_lands_on_the_right_frame(self, reader) -> None:
        shown(reader, moment_of(0))
        assert abs(shown(reader, moment_of(70)) - grey_for(70)) <= GREY_TOLERANCE

    def test_running_past_the_end_holds_the_last_frame(self, reader) -> None:
        """Rather than going blank while the sound plays its last moments."""
        past = reader.picture_at(SECONDS * 1000 * 2)
        assert past is not None

    def test_a_negative_moment_is_read_as_the_beginning(self, reader) -> None:
        assert abs(shown(reader, -500) - grey_for(0)) <= GREY_TOLERANCE


class TestWhenItCannot:
    def test_a_file_that_is_not_there_is_refused(self, tmp_path: pathlib.Path) -> None:
        with pytest.raises(PictureError):
            VideoReader(TrackSource(path=str(tmp_path / "absent.m4v")))

    def test_a_file_with_no_picture_is_refused(self, tmp_path: pathlib.Path) -> None:
        """An ordinary audio file reaching here is a mistake worth saying."""
        from m4a_support import write_m4a

        only_sound = write_m4a(tmp_path / "track.m4a", frames=RATE)
        with pytest.raises(PictureError):
            VideoReader(TrackSource(path=str(only_sound)))


class TestASliceOfAFile:
    def test_a_slice_counts_from_its_own_beginning(self, bonus: pathlib.Path) -> None:
        """A cue track's moment nought is not the file's moment nought."""
        start_frame = RATE  # one second in
        reader = VideoReader(
            TrackSource(path=str(bonus), start_frame=start_frame, end_frame=RATE * 2)
        )
        try:
            at_start = reader.picture_at(0).data[0]
        finally:
            reader.close()
        expected = grey_for(FRAMES_PER_SECOND)
        assert abs(at_start - expected) <= GREY_TOLERANCE
