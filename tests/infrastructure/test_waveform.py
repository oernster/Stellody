"""Measuring a real file and never measuring the same one twice.

Written against real audio rather than a stand-in, because what is being
checked is that the numbers coming out of a decoder describe the sound that
went in. A quiet half and a loud half is the crudest shape that proves the
measurement is following the music rather than the clock.

Nothing here touches the music library: every file is written into a temporary
directory by the test itself.
"""

from __future__ import annotations

import itertools
import pathlib

import numpy as np
import pytest
import soundfile

from stellody.domain.waveform import SILENCE, Envelope, buckets_for
from stellody.infrastructure.waveform import (
    LEVEL_PLACES,
    PROGRESS_SECONDS,
    READ_FRAMES,
    FileWaveforms,
)

SAMPLE_RATE = 44100
SECONDS = 2
QUIET = 0.1
LOUD = 0.9
# Long enough that the reading offers a shape several times, so one offer can
# be aimed at the inside of a bucket rather than at a boundary.
SECONDS_TO_STRADDLE = 60


@pytest.fixture
def cache(tmp_path: pathlib.Path) -> pathlib.Path:
    """Where measurements are kept, never the real directory."""
    return tmp_path / "shapes"


def _two_halves(path: pathlib.Path) -> pathlib.Path:
    """A file that is quiet for its first half and loud for its second."""
    frames = SAMPLE_RATE * SECONDS
    samples = np.zeros((frames, 2), dtype="float32")
    samples[: frames // 2] = QUIET
    samples[frames // 2 :] = LOUD
    soundfile.write(str(path), samples, SAMPLE_RATE, format="FLAC")
    return path


def _long_enough_to_report(path: pathlib.Path) -> pathlib.Path:
    """A file long enough for the reading to offer the shape on its way.

    The offer happens every few seconds of the music, so a file shorter than
    that is finished before there is anything to say about it. That is right
    for a short track and useless for a test of the reporting.
    """
    frames = SAMPLE_RATE * PROGRESS_SECONDS * 3
    samples = np.zeros((frames, 2), dtype="float32")
    samples[frames // 2 :] = LOUD
    soundfile.write(str(path), samples, SAMPLE_RATE, format="FLAC")
    return path


def test_the_shape_follows_the_music(cache, tmp_path) -> None:
    """The whole point: the numbers describe the sound that went in."""
    audio = _two_halves(tmp_path / "halves.flac")
    shape = FileWaveforms(cache).measure(str(audio))
    assert shape is not None
    buckets = buckets_for(SAMPLE_RATE * SECONDS, SAMPLE_RATE)
    assert shape.buckets == buckets
    early = shape.levels[buckets // 4]
    late = shape.levels[buckets * 3 // 4]
    assert early == pytest.approx(QUIET, abs=0.01)
    assert late == pytest.approx(LOUD, abs=0.01)


def test_a_file_is_not_measured_twice(cache, tmp_path) -> None:
    """A decode of a whole file is the expensive thing here."""
    audio = _two_halves(tmp_path / "once.flac")
    counted = _CountingWaveforms(cache)
    first = counted.measure(str(audio))
    second = counted.measure(str(audio))
    assert first == second
    assert counted.decodes == 1, "the second answer came from the kept measurement"


def test_a_measurement_survives_a_restart(cache, tmp_path) -> None:
    """Which is what keeping it in a file rather than in memory is for."""
    audio = _two_halves(tmp_path / "restart.flac")
    measured = FileWaveforms(cache).measure(str(audio))
    remembered = FileWaveforms(cache).remembered(str(audio))
    assert remembered == measured


def test_a_measurement_is_kept_at_the_precision_it_is_drawn_at(cache, tmp_path) -> None:
    """Full precision more than doubles the record for detail nothing shows."""
    audio = _two_halves(tmp_path / "precision.flac")
    shape = FileWaveforms(cache).measure(str(audio))
    assert shape is not None
    assert shape.levels == tuple(round(level, LEVEL_PLACES) for level in shape.levels)


def test_a_file_replaced_at_the_same_name_is_measured_again(cache, tmp_path) -> None:
    """A re-rip is a different file, whatever it is called."""
    audio = tmp_path / "rerip.flac"
    _two_halves(audio)
    FileWaveforms(cache).measure(str(audio))
    frames = SAMPLE_RATE
    soundfile.write(
        str(audio), np.zeros((frames, 2), dtype="float32"), SAMPLE_RATE, format="FLAC"
    )
    assert FileWaveforms(cache).remembered(str(audio)) is None


def test_nothing_is_remembered_about_a_file_never_measured(cache, tmp_path) -> None:
    audio = _two_halves(tmp_path / "fresh.flac")
    assert FileWaveforms(cache).remembered(str(audio)) is None


def test_a_file_that_is_not_there_measures_to_nothing(cache, tmp_path) -> None:
    """A picture that cannot be drawn is not a reason to stop a track."""
    waveforms = FileWaveforms(cache)
    missing = str(tmp_path / "gone.flac")
    assert waveforms.measure(missing) is None
    assert waveforms.remembered(missing) is None
    assert waveforms.frames_in(missing) is None


def test_a_file_that_is_not_audio_measures_to_nothing(cache, tmp_path) -> None:
    rubbish = tmp_path / "notes.txt"
    rubbish.write_text("this is not a flac", encoding="utf-8")
    assert FileWaveforms(cache).measure(str(rubbish)) is None


def test_a_file_holding_no_audio_at_all_has_no_shape(cache, tmp_path) -> None:
    """An empty file opens perfectly well and has nothing in it."""
    audio = tmp_path / "empty.flac"
    soundfile.write(
        str(audio), np.zeros((0, 2), dtype="float32"), SAMPLE_RATE, format="FLAC"
    )
    assert FileWaveforms(cache).measure(str(audio)) is None


def test_the_length_of_a_real_file_is_reported(cache, tmp_path) -> None:
    """A track takes its share of a file's shape by frame, so this decides it."""
    audio = _two_halves(tmp_path / "length.flac")
    assert FileWaveforms(cache).frames_in(str(audio)) == SAMPLE_RATE * SECONDS


def test_a_cache_that_cannot_be_written_is_not_an_error(tmp_path) -> None:
    """The shape is still drawn this time; it is just not kept for next time."""
    audio = _two_halves(tmp_path / "unwritable.flac")
    blocked = tmp_path / "blocked"
    blocked.write_text("a file where a directory would go", encoding="utf-8")
    assert FileWaveforms(blocked).measure(str(audio)) is not None


def test_a_damaged_record_is_ignored_rather_than_believed(cache, tmp_path) -> None:
    """A half written file is not a measurement, whatever it looks like."""
    audio = _two_halves(tmp_path / "damaged.flac")
    waveforms = FileWaveforms(cache)
    waveforms.measure(str(audio))
    for record in cache.iterdir():
        record.write_text("{ not json at all", encoding="utf-8")
    assert waveforms.remembered(str(audio)) is None


class _CountingWaveforms(FileWaveforms):
    """Counts how often it actually reads a file, rather than mocking one."""

    def __init__(self, cache_dir: pathlib.Path) -> None:
        super().__init__(cache_dir)
        self.decodes = 0

    def _levels_of(
        self, path: str, cancelled=None, progress=None
    ) -> tuple[float, ...] | None:
        """Count the decode, then do it."""
        self.decodes += 1
        return super()._levels_of(path, cancelled, progress)


def test_a_measurement_told_to_give_up_keeps_nothing(cache, tmp_path) -> None:
    """Half a file read is not a shape.

    A record of one would be wrong on every redraw afterwards without ever
    looking wrong enough for anybody to notice, so nothing is written and the
    next ask measures the file properly.
    """
    audio = _two_halves(tmp_path / "abandoned.flac")
    waveforms = FileWaveforms(cache)
    assert waveforms.measure(str(audio), cancelled=lambda: True) is None
    assert waveforms.remembered(str(audio)) is None
    assert waveforms.measure(str(audio)) is not None


def test_a_measurement_nobody_stopped_is_kept(cache, tmp_path) -> None:
    audio = _two_halves(tmp_path / "finished.flac")
    waveforms = FileWaveforms(cache)
    measured = waveforms.measure(str(audio), cancelled=lambda: False)
    assert measured is not None
    assert waveforms.remembered(str(audio)) == measured


def _reached(part: Envelope) -> int:
    """How far along the file a partial measurement has got, in buckets."""
    return sum(1 for level in part.levels if level != SILENCE)


def test_the_shape_is_offered_as_it_is_read(cache, tmp_path) -> None:
    """Reading a whole album FLAC through takes 11 seconds, measured cold.

    So the picture builds from the left rather than appearing at the end. The
    file here is short, so what is pinned is that the offer happens at all and
    that the last thing offered is what the measurement came to.
    """
    audio = _long_enough_to_report(tmp_path / "building.flac")
    parts: list[Envelope] = []
    waveforms = FileWaveforms(cache)
    finished = waveforms.measure(str(audio), progress=parts.append)
    assert finished is not None
    assert parts, "nothing was offered on the way"
    # A part is the shape as far as it has been read, so it reaches further
    # each time. What it has finished with does not move again: the only
    # bucket that may still change is the one the reading is inside, which is
    # why the drawn shape does not wobble behind the point it has reached.
    # It is stated as a count rather than as "never falls", because a bucket
    # in progress genuinely can fall: see the test below.
    for earlier, later in itertools.pairwise(parts):
        assert _reached(later) >= _reached(earlier), "the picture grew"
    for part in parts:
        unsettled = [
            index
            for index, (seen, whole) in enumerate(zip(part.levels, finished.levels))
            if seen != whole and seen != SILENCE
        ]
        assert len(unsettled) <= 1, f"more than the frontier moved: {unsettled}"


def test_only_the_finished_measurement_is_kept(cache, tmp_path) -> None:
    """A part written down would be wrong on every redraw afterwards."""
    audio = _long_enough_to_report(tmp_path / "parts.flac")
    kept: list[Envelope | None] = []
    waveforms = FileWaveforms(cache)
    waveforms.measure(
        str(audio), progress=lambda part: kept.append(waveforms.remembered(str(audio)))
    )
    assert kept, "nothing was offered on the way"
    assert all(seen is None for seen in kept), "a part was kept mid measurement"
    assert waveforms.remembered(str(audio)) is not None


def test_a_measurement_given_up_on_offers_nothing_further(cache, tmp_path) -> None:
    audio = _two_halves(tmp_path / "stopped.flac")
    parts: list[Envelope] = []
    assert (
        FileWaveforms(cache).measure(
            str(audio), cancelled=lambda: True, progress=parts.append
        )
        is None
    )
    assert parts == []


def test_the_bucket_being_read_may_fall_before_it_settles(cache, tmp_path) -> None:
    """What the assertion above is stated as a count rather than a direction.

    A bucket holds how loud it is, so a partial one is the loudness of what
    has been folded into it so far. Fold a loud passage, offer the shape, then
    complete that same bucket with quiet frames and it falls. It was tried
    with the transition in the middle of the file and nothing fell, because an
    offer lands inside a bucket only where the arithmetic puts it there; the
    frame is worked out here rather than guessed, which is what made it happen.
    """
    frames = SAMPLE_RATE * SECONDS_TO_STRADDLE
    offer_at = READ_FRAMES
    while offer_at < SAMPLE_RATE * PROGRESS_SECONDS:
        offer_at += READ_FRAMES
    buckets = buckets_for(frames, SAMPLE_RATE)
    bucket = offer_at * buckets // frames
    ends_at = (bucket + 1) * frames // buckets
    audio = tmp_path / "straddle.flac"
    samples = np.full((frames, 1), QUIET, dtype="float32")
    samples[: (offer_at + ends_at) // 2] = LOUD
    soundfile.write(str(audio), samples, SAMPLE_RATE)

    parts: list[Envelope] = []
    finished = FileWaveforms(cache).measure(str(audio), progress=parts.append)
    assert finished is not None
    seen = [part.levels[bucket] for part in parts]
    assert seen[0] > finished.levels[bucket], "the probe did not catch it mid bucket"
    assert min(seen) < seen[0], "the bucket never fell"
    assert seen[-1] == finished.levels[bucket], "it did not settle where it ended"


def test_one_loud_sample_does_not_make_a_bucket_loud(cache, tmp_path) -> None:
    """The fault this measurement was changed for.

    A bucket held the loudest single sample it covered, which is a bucket of
    roughly 120 milliseconds. Any drum, any sustained note, one stray sample:
    each took the whole bucket to the top. Measured over three unlike records,
    that drew more than half of every track at 90 percent of full height, a
    gentle 1998 album included. Loudness is what the drawing is for, so a lone
    spike in an otherwise quiet stretch has to read as a quiet stretch.
    """
    frames = SAMPLE_RATE * SECONDS_TO_STRADDLE
    samples = np.full((frames, 1), QUIET, dtype="float32")
    per_bucket = frames // buckets_for(frames, SAMPLE_RATE)
    samples[::per_bucket] = 1.0
    audio = tmp_path / "spikes.flac"
    soundfile.write(str(audio), samples, SAMPLE_RATE)

    measured = FileWaveforms(cache).measure(str(audio))
    assert measured is not None
    assert measured.loudest < QUIET * 2, (
        "one full scale sample in every bucket took the whole shape to the top: "
        f"loudest bucket is {measured.loudest}"
    )
