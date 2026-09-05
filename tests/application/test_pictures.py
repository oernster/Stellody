"""Holding open the picture of whatever is playing.

Driven through a hand-written port rather than a mocking library, so what is
asserted is the behaviour the real reader has to satisfy: opened once as a
track starts, given up as it ends, never held after the track that needed
it.
"""

from __future__ import annotations

import pytest

from stellody.application.pictures import Pictures
from stellody.domain.picture import Picture
from stellody.domain.playback import PlaybackError
from stellody.domain.track import TrackSource

VIDEO = TrackSource(path="H:/Album/12 Bonus.m4v")
OTHER_VIDEO = TrackSource(path="H:/Album/13 Another.m4v")
SOUND_ONLY = TrackSource(path="H:/Album/01 Song.flac")


def one_picture(value: int = 0) -> Picture:
    """A picture small enough to compare, carrying a value to tell it by."""
    return Picture(width=1, height=1, data=bytes((value, value, value)))


class FakeReader:
    """A picture port that records how it was used."""

    def __init__(self, source: TrackSource) -> None:
        self.source = source
        self.asked: list[int] = []
        self.closed = False

    def picture_at(self, elapsed_ms: int) -> Picture | None:
        self.asked.append(elapsed_ms)
        return one_picture(len(self.asked))

    def close(self) -> None:
        self.closed = True


class Opener:
    """Opens fake readers, remembering every one it made."""

    def __init__(self, failing: bool = False) -> None:
        self.made: list[FakeReader] = []
        self.failing = failing

    def __call__(self, source: TrackSource) -> FakeReader:
        if self.failing:
            raise PlaybackError("this file holds no picture")
        made = FakeReader(source)
        self.made.append(made)
        return made


@pytest.fixture
def opener() -> Opener:
    return Opener()


@pytest.fixture
def pictures(opener: Opener) -> Pictures:
    return Pictures(opener)


class TestFollowingTheTrack:
    def test_nothing_is_showing_before_anything_plays(self, pictures: Pictures) -> None:
        assert pictures.showing is False
        assert pictures.at(0) is None

    def test_a_track_with_a_picture_opens_one(
        self, pictures: Pictures, opener: Opener
    ) -> None:
        pictures.follow(VIDEO)
        assert pictures.showing is True
        assert opener.made[0].source is VIDEO

    def test_a_track_without_a_picture_opens_nothing(
        self, pictures: Pictures, opener: Opener
    ) -> None:
        """The ordinary case: asking is safe for every track."""
        pictures.follow(SOUND_ONLY)
        assert pictures.showing is False
        assert opener.made == []

    def test_nothing_playing_opens_nothing(
        self, pictures: Pictures, opener: Opener
    ) -> None:
        pictures.follow(None)
        assert pictures.showing is False
        assert opener.made == []

    def test_the_same_track_is_opened_once(
        self, pictures: Pictures, opener: Opener
    ) -> None:
        """It is called on every tick, so it must not reopen the file."""
        pictures.follow(VIDEO)
        pictures.follow(VIDEO)
        pictures.follow(VIDEO)
        assert len(opener.made) == 1
        assert opener.made[0].closed is False

    def test_moving_to_another_track_gives_the_first_file_back(
        self, pictures: Pictures, opener: Opener
    ) -> None:
        pictures.follow(VIDEO)
        pictures.follow(OTHER_VIDEO)
        assert opener.made[0].closed is True
        assert opener.made[1].source is OTHER_VIDEO

    def test_moving_to_a_track_with_no_picture_gives_the_file_back(
        self, pictures: Pictures, opener: Opener
    ) -> None:
        pictures.follow(VIDEO)
        pictures.follow(SOUND_ONLY)
        assert opener.made[0].closed is True
        assert pictures.showing is False

    def test_stopping_gives_the_file_back(
        self, pictures: Pictures, opener: Opener
    ) -> None:
        pictures.follow(VIDEO)
        pictures.follow(None)
        assert opener.made[0].closed is True
        assert pictures.showing is False


class TestAskingWhatIsShowing:
    def test_it_asks_the_reader_for_the_moment_given(
        self, pictures: Pictures, opener: Opener
    ) -> None:
        pictures.follow(VIDEO)
        pictures.at(1234)
        assert opener.made[0].asked == [1234]

    def test_nothing_is_asked_of_a_track_with_no_picture(
        self, pictures: Pictures
    ) -> None:
        pictures.follow(SOUND_ONLY)
        assert pictures.at(1234) is None


class TestWhenTheFileWillNotOpen:
    def test_the_sound_is_left_playing(self) -> None:
        """Taking the track away would lose the half that was working."""
        pictures = Pictures(Opener(failing=True))
        pictures.follow(VIDEO)
        assert pictures.showing is False
        assert pictures.at(0) is None

    def test_it_is_tried_again_for_the_next_track(self) -> None:
        """A failure is not remembered as a decision about every file."""
        opener = Opener(failing=True)
        pictures = Pictures(opener)
        pictures.follow(VIDEO)
        opener.failing = False
        pictures.follow(OTHER_VIDEO)
        assert pictures.showing is True


class TestClosing:
    def test_closing_twice_is_harmless(
        self, pictures: Pictures, opener: Opener
    ) -> None:
        pictures.follow(VIDEO)
        pictures.close()
        pictures.close()
        assert opener.made[0].closed is True
        assert pictures.showing is False

    def test_a_track_can_be_opened_again_after_closing(
        self, pictures: Pictures, opener: Opener
    ) -> None:
        pictures.follow(VIDEO)
        pictures.close()
        pictures.follow(VIDEO)
        assert len(opener.made) == 2
        assert pictures.showing is True
