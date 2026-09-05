"""Reading audio frames out of a file, including one cue sheet track of it.

soundfile seeks and reads by frame, so a cue slice needs no special handling
beyond starting in the right place and refusing to run past the end. That is
the whole reason this layer is thin: the slice abstraction the domain models is
something the decoder already understands.

Not every format is addressable that way. `packet_decode.py` holds the reader
for the compressed ones, which arrive as packets and have to be counted into
place; `open_source` below chooses between the two by suffix and hands back
something satisfying `AudioSource` either way, so nothing above here knows
which it holds.
"""

from __future__ import annotations

from types import TracebackType
from typing import Protocol, Self

import numpy as np
import soundfile

from stellody.domain.playback import PlaybackError
from stellody.domain.track import PICTURE_SUFFIXES, TrackSource

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

# Suffixes libsndfile cannot open, which the packet reader takes instead. Kept
# here rather than in the walker because it is a property of the decoders;
# the walker's own sets answer a different question: what a library holds.
#
# The picture-bearing containers join it rather than needing a reader of their
# own: .m4v is the MP4 container .m4a already arrives in, with AAC beside the
# H.264. Measured, not assumed: the packet reader was pointed at video files
# off the reference library unmodified and decoded their sound correctly. The
# picture is read separately by whatever shows it; nothing on the sound path
# knows a picture is there.
PACKET_SUFFIXES = frozenset({".m4a"}) | PICTURE_SUFFIXES


class DecodeError(PlaybackError):
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


class AudioSource(Protocol):
    """What the engine and the waveform need of an open source.

    `SourceReader` and `PacketReader` both satisfy this, so the two are
    interchangeable at every point above this module.
    """

    @property
    def sample_rate(self) -> int:
        """The source's own sample rate."""

    @property
    def channels(self) -> int:
        """How many channels the source carries."""

    @property
    def bit_depth(self) -> int:
        """The stored depth; nought when the format states none."""

    @property
    def frame_count(self) -> int:
        """How many frames this slice holds."""

    @property
    def frame(self) -> int:
        """The next frame to be read, relative to the slice start."""

    @property
    def dtype(self) -> str:
        """The sample type this reader hands back."""

    def seek(self, frame: int) -> None:
        """Move to a frame within the slice, clamped to both of its ends."""

    def read(self, frames: int) -> np.ndarray:
        """Up to `frames` frames, always two dimensional."""

    def close(self) -> None:
        """Release the source. Safe to call more than once."""

    def __enter__(self) -> Self:
        """Support use as a context manager."""

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Close the source however the block ends."""


def open_source(source: TrackSource, dtype: str = WORKING_DTYPE) -> AudioSource:
    """Open a track source with whichever reader can decode it.

    The packet reader is imported here rather than at module scope because
    importing it loads a shared FFmpeg build of some sixty megabytes. A library
    holding no compressed formats never pays for it; one holding a few pays
    only when a track from them is actually opened.
    """
    if _suffix_of(source.path) in PACKET_SUFFIXES:
        try:
            from stellody.infrastructure.packet_decode import PacketReader
        except ImportError as error:
            # The decoder is a dependency like any other and it can be absent:
            # a checkout whose requirements have not been installed is the
            # ordinary case. Left to escape, it reached the window as nothing
            # happening at all, which is the one answer a listener cannot act
            # on. Said plainly here instead, it names what is missing.
            raise DecodeError(
                f"cannot decode {source.path}: the decoder for this format "
                f"is not installed ({error})"
            ) from error
        return PacketReader(source, dtype=dtype)
    return SourceReader(source, dtype=dtype)


def _suffix_of(path: str) -> str:
    """The lower-cased extension of a path, empty when it has none."""
    dot = path.rfind(".")
    slash = max(path.rfind("/"), path.rfind("\\"))
    return path[dot:].casefold() if dot > slash else ""
