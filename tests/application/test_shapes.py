"""A track's share of the shape of the file it lives in.

Two answers rather than one, deliberately: an instant one that may know
nothing and a slow one that settles it. The interface draws the first and
puts the second on a thread, so a track starts playing now rather than once
its picture is ready.

The measurement is kept against the FILE, which is what makes the second track
of a cue-sheet album arrive with its shape already there.
"""

from __future__ import annotations

import pytest

from stellody.application.shapes import TrackShapes
from stellody.domain.track import TrackSource
from stellody.domain.waveform import Envelope

FILE_FRAMES = 1000
WHOLE = Envelope(peaks=tuple(index / 10 for index in range(10)))


class FakeWaveforms:
    """A stand-in that measures nothing and records what it was asked."""

    def __init__(
        self,
        known: Envelope | None = None,
        measurable: Envelope | None = WHOLE,
        frames: int | None = FILE_FRAMES,
        parts: tuple[Envelope, ...] = (),
    ) -> None:
        self.known = known
        self.measurable = measurable
        self.parts = parts
        self.frames = frames
        self.asked: list[str] = []

    def remembered(self, path: str) -> Envelope | None:
        """What is already known about this file."""
        self.asked.append(f"remembered {path}")
        return self.known

    def measure(self, path: str, cancelled=None, progress=None) -> Envelope | None:
        """What measuring it would find, unless it is told to give up.

        The parts are offered first when a test asked for any, so what the
        service does with them is watched rather than assumed.
        """
        self.asked.append(f"measure {path}")
        if cancelled is not None and cancelled():
            return None
        for part in self.parts:
            if progress is not None:
                progress(part)
        return self.measurable

    def frames_in(self, path: str) -> int | None:
        """How long the file is."""
        return self.frames


def test_a_file_never_measured_is_not_waited_for() -> None:
    """The instant question has to be able to answer nothing."""
    waveforms = FakeWaveforms(known=None)
    assert TrackShapes(waveforms).remembered(TrackSource(path="a.flac")) is None
    assert waveforms.asked == ["remembered a.flac"], "it did not decode anything"


def test_a_whole_file_track_takes_the_whole_shape() -> None:
    shapes = TrackShapes(FakeWaveforms(known=WHOLE))
    assert shapes.remembered(TrackSource(path="a.flac")) == WHOLE


def test_a_cue_track_takes_only_its_own_part_of_the_file() -> None:
    """The reason the measurement is kept against the file rather than a track."""
    shapes = TrackShapes(FakeWaveforms(known=WHOLE))
    part = shapes.remembered(
        TrackSource(path="album.flac", start_frame=0, end_frame=FILE_FRAMES // 2)
    )
    assert part is not None
    assert part.buckets == WHOLE.buckets // 2


def test_a_cue_track_running_to_the_end_of_the_file_reaches_it() -> None:
    """An end of None means the rest of the file, which has to be found."""
    shapes = TrackShapes(FakeWaveforms(known=WHOLE))
    part = shapes.remembered(
        TrackSource(path="album.flac", start_frame=FILE_FRAMES // 2)
    )
    assert part is not None
    assert part.peaks[-1] == pytest.approx(WHOLE.peaks[-1])


def test_measuring_decodes_and_answers() -> None:
    waveforms = FakeWaveforms(known=None, measurable=WHOLE)
    assert TrackShapes(waveforms).measured(TrackSource(path="a.flac")) == WHOLE
    assert waveforms.asked == ["measure a.flac"]


def test_a_file_that_cannot_be_measured_simply_has_no_shape() -> None:
    """A picture that cannot be drawn is no reason to stop a track playing."""
    shapes = TrackShapes(FakeWaveforms(measurable=None))
    assert shapes.measured(TrackSource(path="gone.flac")) is None


def test_a_file_whose_length_is_unknown_has_no_shape_to_share_out() -> None:
    """Without a length there is no way to say which part is this track's."""
    shapes = TrackShapes(FakeWaveforms(known=WHOLE, frames=None))
    assert shapes.remembered(TrackSource(path="a.flac", start_frame=1)) is None


def test_a_file_of_no_length_has_no_shape_either() -> None:
    shapes = TrackShapes(FakeWaveforms(known=WHOLE, frames=0))
    assert shapes.remembered(TrackSource(path="a.flac", start_frame=1)) is None


def test_a_measurement_can_be_given_up_on() -> None:
    """A whole album FLAC takes 22 seconds to read, measured.

    Carrying on with one the highlight has moved off costs a core for a
    picture nobody will see, so the check is handed down to the reader rather
    than the answer being thrown away after the fact.
    """
    waveforms = FakeWaveforms(measurable=WHOLE)
    shapes = TrackShapes(waveforms)
    assert shapes.measured(TrackSource(path="a.flac"), cancelled=lambda: True) is None
    assert waveforms.asked == ["measure a.flac"]


def test_a_measurement_nobody_stopped_still_answers() -> None:
    waveforms = FakeWaveforms(measurable=WHOLE)
    shapes = TrackShapes(waveforms)
    assert shapes.measured(TrackSource(path="a.flac"), cancelled=lambda: False) == WHOLE


def test_each_part_measured_is_offered_as_it_arrives() -> None:
    """The picture builds from the left rather than appearing at the end."""
    parts = (Envelope(peaks=(0.1, 0.0)), Envelope(peaks=(0.1, 0.4)))
    waveforms = FakeWaveforms(measurable=WHOLE, parts=parts)
    offered: list[Envelope] = []
    TrackShapes(waveforms).measured(TrackSource(path="a.flac"), progress=offered.append)
    assert offered == list(parts)


def test_a_part_of_a_cue_sheet_album_is_cut_to_the_track_it_belongs_to() -> None:
    """One file holds the whole album, so the part read is the album's.

    Handing that on unchanged would draw the album's shape building up on
    every track of it.
    """
    parts = (WHOLE,)
    waveforms = FakeWaveforms(measurable=WHOLE, parts=parts)
    slice_of = TrackSource(path="a.flac", start_frame=0, end_frame=FILE_FRAMES // 2)
    offered: list[Envelope] = []
    TrackShapes(waveforms).measured(slice_of, progress=offered.append)
    assert offered and offered[0] != WHOLE


def test_a_part_that_cuts_to_nothing_is_not_offered() -> None:
    """A track whose file reports no length has no share of anything."""
    waveforms = FakeWaveforms(measurable=WHOLE, parts=(WHOLE,), frames=None)
    offered: list[Envelope] = []
    TrackShapes(waveforms).measured(TrackSource(path="a.flac"), progress=offered.append)
    assert offered == []
