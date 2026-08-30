"""Measuring how loud a file is all the way along, then keeping the answer.

Measuring means decoding the whole file, which takes about as long as anything
Stellody does. It is worth doing once and never again, so the answer is kept
in Stellody's own directory beside the artwork, never in the music folder.

The file is read in blocks and the loudest sample in each is folded into a
bucket, so a long file costs no more memory than a short one: nothing here
holds a whole track.

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
from stellody.domain.waveform import BUCKETS, Envelope, envelope_from
from stellody.infrastructure.decode import DecodeError, SourceReader

# Frames per read. Large enough that a long file is not thousands of calls,
# small enough that one block is a modest array whatever the file's depth.
READ_FRAMES = 1 << 16
CACHE_SUFFIX = ".json"
FORMAT_VERSION = 1
PEAK_PLACES = 4


def _kept(peaks: tuple[float, ...]) -> tuple[float, ...]:
    """Peaks at the precision a record holds, which is what is drawn.

    Four places is finer than a display can show and keeps the record small;
    a whole file measures to a few kilobytes.
    """
    return tuple(round(peak, PEAK_PLACES) for peak in peaks)


class FileWaveforms:
    """Measures files; remembers what it measured."""

    def __init__(self, cache_dir: pathlib.Path) -> None:
        self._cache_dir = cache_dir

    def remembered(self, path: str) -> Envelope | None:
        """The shape of this file if it has been measured; None otherwise."""
        record = self._read_record(path)
        if record is None:
            return None
        return envelope_from(tuple(record["peaks"]))

    def measure(self, path: str, cancelled=None) -> Envelope | None:
        """The shape of this file, measuring it unless it is already known.

        A measurement given up on keeps nothing and answers None: half a file
        read is not a shape; a record of one would be wrong on every redraw
        afterwards without ever looking wrong enough to notice.
        """
        known = self.remembered(path)
        if known is not None:
            return known
        peaks = self._peaks_of(path, cancelled)
        if peaks is None:
            return None
        # Rounded here rather than on the way to the file, so a shape is the
        # same whether it has just been measured or read back afterwards. A
        # measurement that differed from its own record by a rounding would
        # redraw slightly differently after a restart, for no reason anybody
        # could see.
        envelope = envelope_from(_kept(peaks))
        self._write_record(path, envelope)
        return envelope

    def frames_in(self, path: str) -> int | None:
        """How many frames the whole file holds; None when it cannot be read."""
        try:
            with SourceReader(TrackSource(path=path)) as reader:
                return reader.frame_count
        except (DecodeError, OSError, ValueError):
            return None

    def _peaks_of(self, path: str, cancelled=None) -> tuple[float, ...] | None:
        """The loudest sample in each bucket of the file; None if unreadable."""
        try:
            with SourceReader(TrackSource(path=path)) as reader:
                frames = reader.frame_count
                if frames <= 0:
                    return None
                return self._fold(reader, frames, cancelled)
        except (DecodeError, OSError, ValueError):
            return None

    def _fold(
        self, reader: SourceReader, frames: int, cancelled=None
    ) -> tuple[float, ...] | None:
        """Read the file through, keeping the loudest sample per bucket.

        The give-up check sits at the block boundary, which is the only place
        a decode can be stopped without leaving the reader half way through
        something. Measured on a whole album FLAC of 390 megabytes, reading it
        through takes 22 seconds, so a measurement nobody wants any more is
        worth stopping rather than waiting out.
        """
        peaks = [0.0] * BUCKETS
        seen = 0
        while True:
            if cancelled is not None and cancelled():
                return None
            block = reader.read(READ_FRAMES)
            if block.shape[0] == 0:
                break
            loudest = np.max(np.abs(block), axis=1)
            for offset, level in enumerate(loudest):
                bucket = min(BUCKETS - 1, (seen + offset) * BUCKETS // frames)
                if level > peaks[bucket]:
                    peaks[bucket] = float(level)
            seen += block.shape[0]
        return tuple(peaks)

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
        if not record.get("peaks"):
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
            "peaks": list(envelope.peaks),
        }
        try:
            self._cache_dir.mkdir(parents=True, exist_ok=True)
            self._record_path(path).write_text(
                json.dumps(record, separators=(",", ":")), encoding="utf-8"
            )
        except OSError:
            return
