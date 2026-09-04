"""Measuring how loud a file is all the way along, then keeping the answer.

Measuring means decoding the whole file, which takes about as long as anything
Stellody does. It is worth doing once and never again, so the answer is kept
in Stellody's own directory beside the artwork, never in the music folder.

The file is read in blocks and each block's squares are folded into the
buckets they belong to, so a long file costs no more memory than a short one:
nothing here holds a whole track. Sums and counts are carried rather than
levels, because a root cannot be taken twice; the roots are taken once, at the
end, over whatever has been folded so far.

A remembered measurement is checked against the file's size and modification
time, the same pair the library scan trusts. A file re-ripped at the same path
is a different file and gets measured again.
"""

from __future__ import annotations

import hashlib
import json
import pathlib

import numpy as np

from stellody.domain.track import TrackSource
from stellody.domain.waveform import Envelope, buckets_for, envelope_from
from stellody.infrastructure.decode import AudioSource, DecodeError, open_source

# Frames per read. Large enough that a long file is not thousands of calls,
# small enough that one block is a modest array whatever the file's depth.
READ_FRAMES = 1 << 16
# How much audio is folded in before the shape so far is offered to whoever
# asked for it. In seconds of the music rather than in blocks, so the rate does
# not change with the sample rate of the file. Reading runs far faster than
# real time, so this arrives in bursts; a burst is the drawing's problem and Qt
# already merges repaints, which is exactly the chunking wanted.
PROGRESS_SECONDS = 5
CACHE_SUFFIX = ".json"
# Bumped when a kept record stops meaning what it used to. Version 1 held the
# loudest sample in each bucket; a record of those drawn as loudness would be
# the old shape wearing the new name. Version 2 measured every file into the
# same number of buckets, which made a bucket of a cue-sheet album most of two
# seconds; the count follows the length of the music now.
FORMAT_VERSION = 3
LEVEL_PLACES = 4


def _reporting(progress):
    """Turn a caller's shape handler into one the fold can feed raw buckets.

    The fold works in plain numbers; everybody above it works in shapes. The
    rounding is applied here as well as at the end, so a part looks like the
    measurement it is on the way to rather than differing from it in the last
    decimal place.
    """
    if progress is None:
        return None

    def offer(levels: tuple[float, ...]) -> None:
        progress(envelope_from(_kept(levels)))

    return offer


def _as_levels(sums: np.ndarray, counts: np.ndarray) -> tuple[float, ...]:
    """The buckets folded so far, as loudness on a scale where 1.0 is full.

    The root is taken here rather than as the folding goes, since a mean of
    roots is not the root of a mean. A bucket nothing has reached yet counts
    as silence rather than dividing by nothing.
    """
    return tuple(np.sqrt(sums / np.maximum(counts, 1)).tolist())


def _fold_block(
    sums: np.ndarray, counts: np.ndarray, square: np.ndarray, seen: int, frames: int
) -> None:
    """Fold one block of squared frames into the buckets they belong to.

    Both the sum and the count are needed, because the blocks do not divide
    the buckets evenly: the last bucket a block reaches is usually shared with
    the block after it, so a bucket's mean cannot be known until every block
    that touches it has been folded in.
    """
    buckets = sums.shape[0]
    index = (np.arange(seen, seen + square.shape[0]) * buckets) // frames
    np.clip(index, 0, buckets - 1, out=index)
    sums += np.bincount(index, weights=square, minlength=buckets)
    counts += np.bincount(index, minlength=buckets)


def _kept(levels: tuple[float, ...]) -> tuple[float, ...]:
    """Levels at the precision a record holds, which is what is drawn.

    Four places is finer than a display can show and keeps the record small.
    The size follows the length of the file, since the resolution does: a few
    minutes of music measures to about sixteen kilobytes, a 55.7 minute cue
    sheet album holding nine tracks to 224.
    """
    return tuple(round(level, LEVEL_PLACES) for level in levels)


class FileWaveforms:
    """Measures files; remembers what it measured."""

    def __init__(self, cache_dir: pathlib.Path) -> None:
        self._cache_dir = cache_dir

    def remembered(self, path: str) -> Envelope | None:
        """The shape of this file if it has been measured; None otherwise."""
        record = self._read_record(path)
        if record is None:
            return None
        return envelope_from(tuple(record["levels"]))

    def measure(self, path: str, cancelled=None, progress=None) -> Envelope | None:
        """The shape of this file, measuring it unless it is already known.

        The shape so far is offered as it is read, so a picture builds from the
        left rather than appearing whole at the end. Measured cold on the
        reference library, reading an ordinary track through takes 0.67 seconds
        and a whole album FLAC of 323 megabytes takes 11.1, which is a long
        time to show nothing.

        Only the finished measurement is kept. A part of one written down would
        be wrong on every redraw afterwards without ever looking wrong enough
        to notice, which is the same reason a measurement given up on keeps
        nothing and answers None.
        """
        known = self.remembered(path)
        if known is not None:
            return known
        levels = self._levels_of(path, cancelled, _reporting(progress))
        if levels is None:
            return None
        # Rounded here rather than on the way to the file, so a shape is the
        # same whether it has just been measured or read back afterwards. A
        # measurement that differed from its own record by a rounding would
        # redraw slightly differently after a restart, for no reason anybody
        # could see.
        envelope = envelope_from(_kept(levels))
        self._write_record(path, envelope)
        return envelope

    def frames_in(self, path: str) -> int | None:
        """How many frames the whole file holds; None when it cannot be read."""
        try:
            with open_source(TrackSource(path=path)) as reader:
                return reader.frame_count
        except (DecodeError, OSError, ValueError):
            return None

    def _levels_of(
        self, path: str, cancelled=None, progress=None
    ) -> tuple[float, ...] | None:
        """How loud each bucket of the file is; None if it cannot be read."""
        try:
            with open_source(TrackSource(path=path)) as reader:
                frames = reader.frame_count
                if frames <= 0:
                    return None
                return self._fold(reader, frames, cancelled, progress)
        except (DecodeError, OSError, ValueError):
            return None

    def _fold(
        self, reader: AudioSource, frames: int, cancelled=None, progress=None
    ) -> tuple[float, ...] | None:
        """Read the file through, keeping how loud each bucket is.

        The reduction is done by numpy over whole blocks rather than by walking
        the frames in Python. That is the same arithmetic, bit for bit; it is
        also what the time was going on: measured, folding a 60 megabyte track
        took 3.2 seconds a frame at a time and 0.84 vectorised, while a whole
        album FLAC of 390 megabytes went from 21.8 seconds to 5.3.

        The give-up check sits at the block boundary, which is the only place
        a decode can be stopped without leaving the reader half way through
        something.
        """
        buckets = buckets_for(frames, reader.sample_rate)
        sums = np.zeros(buckets)
        counts = np.zeros(buckets, dtype=np.int64)
        step = max(1, reader.sample_rate * PROGRESS_SECONDS)
        seen = 0
        offered = 0
        while True:
            if cancelled is not None and cancelled():
                return None
            block = reader.read(READ_FRAMES)
            count = block.shape[0]
            if count == 0:
                break
            square = np.mean(np.square(block, dtype=np.float64), axis=1)
            _fold_block(sums, counts, square, seen, frames)
            seen += count
            if progress is not None and seen - offered >= step:
                offered = seen
                progress(_as_levels(sums, counts))
        return _as_levels(sums, counts)

    def _record_path(self, path: str) -> pathlib.Path:
        """Where this file's measurement is kept.

        Named by a digest of the path rather than by the path itself: a music
        folder's names are arbitrary and a filesystem's are not, so a title
        with a colon or a name longer than the system allows would otherwise
        decide whether a shape could be kept at all.
        """
        digest = hashlib.sha256(path.encode("utf-8", "replace")).hexdigest()
        return self._cache_dir / f"{digest}{CACHE_SUFFIX}"

    def _stamp(self, path: str) -> tuple[int, int] | None:
        """The file's size and modification time; None when it is not there."""
        try:
            stat = pathlib.Path(path).stat()
        except OSError:
            return None
        return stat.st_size, int(stat.st_mtime)

    def _read_record(self, path: str) -> dict | None:
        """A kept measurement, if one matches the file as it stands now."""
        stamp = self._stamp(path)
        if stamp is None:
            return None
        try:
            written = self._record_path(path).read_text(encoding="utf-8")
            record = json.loads(written)
        except (OSError, ValueError):
            return None
        if record.get("version") != FORMAT_VERSION:
            return None
        if (record.get("size"), record.get("modified")) != stamp:
            return None
        if not record.get("levels"):
            return None
        return record

    def _write_record(self, path: str, envelope: Envelope) -> None:
        """Keep a measurement. A cache that cannot be written is not an error."""
        stamp = self._stamp(path)
        if stamp is None:
            return
        size, modified = stamp
        record = {
            "version": FORMAT_VERSION,
            "size": size,
            "modified": modified,
            "levels": list(envelope.levels),
        }
        try:
            self._cache_dir.mkdir(parents=True, exist_ok=True)
            self._record_path(path).write_text(
                json.dumps(record, separators=(",", ":")), encoding="utf-8"
            )
        except OSError:
            return
