"""Measuring a real file and never measuring the same one twice.

Written against real audio rather than a stand-in, because what is being
checked is that the numbers coming out of a decoder describe the sound that
went in. A quiet half and a loud half is the crudest shape that proves the
measurement is following the music rather than the clock.

Nothing here touches the music library: every file is written into a temporary
directory by the test itself.
"""

from __future__ import annotations

import pathlib

import numpy as np
import pytest
import soundfile

from stellody.domain.waveform import BUCKETS
from stellody.infrastructure.waveform import PEAK_PLACES, FileWaveforms

SAMPLE_RATE = 44100
SECONDS = 2
QUIET = 0.1
LOUD = 0.9


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


def test_the_shape_follows_the_music(cache, tmp_path) -> None:
    """The whole point: the numbers describe the sound that went in."""
    audio = _two_halves(tmp_path / "halves.flac")
    shape = FileWaveforms(cache).measure(str(audio))
    assert shape is not None
    assert shape.buckets == BUCKETS
    early = shape.peaks[BUCKETS // 4]
    late = shape.peaks[BUCKETS * 3 // 4]
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
    assert shape.peaks == tuple(round(peak, PEAK_PLACES) for peak in shape.peaks)


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

    def _peaks_of(self, path: str) -> tuple[float, ...] | None:
        """Count the decode, then do it."""
        self.decodes += 1
        return super()._peaks_of(path)
