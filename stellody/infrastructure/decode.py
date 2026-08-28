"""Reading audio frames out of a file, including one cue sheet track of it.

soundfile seeks and reads by frame, so a cue slice needs no special handling
beyond starting in the right place and refusing to run past the end. That is
the whole reason this layer is thin: the slice abstraction the domain models is
something the decoder already understands.
"""

from __future__ import annotations

from types import TracebackType
from typing import Self

import numpy as np
import soundfile

from stellody.domain.track import TrackSource

SUBTYPE_BIT_DEPTHS = {
    "PCM_S8": 8,
    "PCM_U8": 8,
    "PCM_16": 16,
    "PCM_24": 24,
    "PCM_32": 32,
    "FLOAT": 32,
    "DOUBLE": 64,
}
DEFAULT_BIT_DEPTH = 16
WORKING_DTYPE = "float32"


class DecodeError(RuntimeError):
    """Raised when a source cannot be opened or read at all."""


class SourceReader:
    """One open audio source, positioned within its own slice.

    Every frame index this class accepts or reports is relative to the START of
    the slice, so a cue track and a whole file behave identically to a caller.
    """

    def __init__(self, source: TrackSource, dtype: str = WORKING_DTYPE) -> None:
        self._source = source
        self._dtype = dtype
        try:
            self._handle = soundfile.SoundFile(source.path)
        except (RuntimeError, OSError) as error:
            raise DecodeError(f"cannot open {source.path}: {error}") from error
        self._start = min(source.start_frame, self._handle.frames)
        end = source.end_frame
        limit = self._handle.frames if end is None else min(end, self._handle.frames)
        self._frame_count = max(0, limit - self._start)
        self.seek(0)

    def __enter__(self) -> Self:
        """Support use as a context manager."""
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Close the underlying file however the block ends."""
        self.close()

    @property
    def sample_rate(self) -> int:
        """The file's own sample rate."""
        return int(self._handle.samplerate)

    @property
    def channels(self) -> int:
        """How many channels the file carries."""
        return int(self._handle.channels)

    @property
    def bit_depth(self) -> int:
        """The file's stored depth; the CD depth when the subtype is unknown."""
        return SUBTYPE_BIT_DEPTHS.get(self._handle.subtype, DEFAULT_BIT_DEPTH)

    @property
    def frame_count(self) -> int:
        """How many frames this slice holds."""
        return self._frame_count

    @property
    def frame(self) -> int:
        """The next frame to be read, relative to the slice start."""
        return max(0, int(self._handle.tell()) - self._start)

    def seek(self, frame: int) -> None:
        """Move to a frame within the slice, clamped to both of its ends."""
        target = min(max(0, frame), self._frame_count)
        self._handle.seek(self._start + target)

    @property
    def dtype(self) -> str:
        """The sample type this reader hands back."""
        return self._dtype

    def read(self, frames: int) -> np.ndarray:
        """Up to `frames` frames in this reader's dtype, always two dimensional.

        Returns an empty array at the end of the slice, which is how the feeder
        thread learns the track is over.
        """
        wanted = min(frames, self._frame_count - self.frame)
        if wanted <= 0:
            return np.zeros((0, self.channels), dtype=self._dtype)
        try:
            block = self._handle.read(wanted, dtype=self._dtype, always_2d=True)
        except RuntimeError as error:
            raise DecodeError(f"cannot read {self._source.path}: {error}") from error
        return block

    def close(self) -> None:
        """Release the file handle. Safe to call more than once."""
        if not self._handle.closed:
            self._handle.close()
