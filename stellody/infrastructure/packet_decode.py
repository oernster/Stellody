"""Reading audio frames out of a file libsndfile cannot open.

`decode.py` holds the reader for everything soundfile understands. This module
holds the other one, for compressed formats that arrive as packets rather than
as addressable PCM. It presents exactly the same surface, so the engine, the
waveform and the cue-sheet slice abstraction never learn which one they hold.

**Three measurements shape this file**, all taken against real files rather
than read out of a manual.

A packet stream has no frame index. Positions are carried as presentation
timestamps and the timestamp of the first decoded packet is not nought: an AAC
file written by iTunes starts at 2112, the encoder priming the decoder has
already discarded by the time samples appear. Every timestamp here is
translated through that offset, measured from the file at open time rather
than assumed, because a reader that ignored it started every track 48
milliseconds into itself.

A seek is not exact on its own. Landing on the packet containing the wanted
frame and decoding from there gives audio that differs audibly from the same
frame reached by playing forward, because the codec needs the packet before it
to reconstruct the overlap. Decoding a short run before the target and throwing
it away removes the difference entirely: measured across four seek targets in a
real file, one packet of pre-roll took the largest sample difference from 0.5
to nought exactly. Two are used, so the margin does not rest on one reading.

The length a container states is not the length that decodes. An iTunes file
overstates by exactly its priming, every time, across all twenty one tracks of
the album this was measured on. A file FFmpeg wrote itself understates instead,
because the trailing encoder padding decodes as real packets. Subtracting the
priming is exact for the first case and conservative for the second; reads
stop at whichever arrives first, the stated length or the end of the packets,
so neither case can run past the end of the audio.
"""

from __future__ import annotations

from types import TracebackType
from typing import Self

import av
import numpy as np

from stellody.domain.track import TrackSource
from stellody.infrastructure.decode import WORKING_DTYPE, DecodeError

# The numpy dtype the engine asks for, spelled as the resampler spells it.
RESAMPLER_FORMATS = {"float32": "flt", "int32": "s32", "int16": "s16"}

# Packets decoded and discarded before the wanted frame after a seek. One was
# measured to be enough; two is the margin.
PREROLL_PACKETS = 2

# The packet length to assume when the codec states none of its own.
ASSUMED_PACKET_FRAMES = 1024


class PacketReader:
    """One open packet stream, positioned within its own slice.

    Every frame index this class accepts or reports is relative to the START of
    the slice, exactly as `SourceReader` does, so a caller holding one of these
    cannot tell which reader it has.
    """

    def __init__(self, source: TrackSource, dtype: str = WORKING_DTYPE) -> None:
        self._source = source
        self._dtype = dtype
        self._format = RESAMPLER_FORMATS.get(dtype)
        if self._format is None:
            raise DecodeError(f"cannot decode {source.path} as {dtype}")
        try:
            self._container = av.open(source.path)
        except (av.FFmpegError, OSError, ValueError) as error:
            raise DecodeError(f"cannot open {source.path}: {error}") from error
        try:
            self._stream = self._container.streams.audio[0]
        except IndexError:
            self._container.close()
            raise DecodeError(f"no audio in {source.path}") from None
        codec = self._stream.codec_context
        self._sample_rate = int(codec.sample_rate or 0)
        self._channels = int(codec.layout.nb_channels)
        self._packet_frames = int(codec.frame_size or ASSUMED_PACKET_FRAMES)
        if self._sample_rate <= 0 or self._channels <= 0:
            self._container.close()
            raise DecodeError(f"{source.path} states no usable audio format")
        self._priming = self._measure_priming()
        self._frame_count = self._slice_frames()
        self._decoded: list[np.ndarray] = []
        self._held = 0
        self._position = 0
        self._frames: object = iter(())
        self._resampler: av.AudioResampler | None = None
        self._exhausted = True
        # Where the held buffer starts, as an absolute frame index. Unknown
        # until the first packet after a seek states its own timestamp.
        self._buffer_at: int | None = None
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
        """Close the container however the block ends."""
        self.close()

    @property
    def sample_rate(self) -> int:
        """The stream's own sample rate."""
        return self._sample_rate

    @property
    def channels(self) -> int:
        """How many channels the stream carries."""
        return self._channels

    @property
    def bit_depth(self) -> int:
        """No stated depth, always, because this reader cannot know one.

        The container states the stored depth and the probe is what reads it.
        What arrives here is the format the decoder chose to hand back, which
        is a different number: measured on a 24 bit ALAC file, FFmpeg decodes
        into a 32 bit format and reports nothing about the 24. Answering with
        the decode format would therefore invent a depth the file never
        carried, so nothing is claimed instead.
        """
        return 0

    @property
    def frame_count(self) -> int:
        """How many frames this slice holds."""
        return self._frame_count

    @property
    def frame(self) -> int:
        """The next frame to be read, relative to the slice start."""
        return self._position

    @property
    def dtype(self) -> str:
        """The sample type this reader hands back."""
        return self._dtype

    def seek(self, frame: int) -> None:
        """Move to a frame within the slice, clamped to both of its ends."""
        target = min(max(0, frame), self._frame_count)
        absolute = self._source.start_frame + target
        preroll = self._packet_frames * PREROLL_PACKETS
        self._restart(max(0, absolute - preroll))
        self._position = target
        self._discard_to(absolute)

    def read(self, frames: int) -> np.ndarray:
        """Up to `frames` frames in this reader's dtype, always two dimensional.

        Returns an empty array at the end of the slice, which is how the feeder
        thread learns the track is over. The end is whichever arrives first,
        the stated length or the last packet the file actually holds.
        """
        wanted = min(frames, self._frame_count - self._position)
        if wanted <= 0:
            return self._empty()
        block = self._take(wanted)
        self._position += block.shape[0]
        return block

    def close(self) -> None:
        """Release the container. Safe to call more than once."""
        if self._container is not None:
            self._container.close()
            self._container = None  # type: ignore[assignment]

    def _measure_priming(self) -> int:
        """Frames of encoder priming the timestamps carry and the samples do not."""
        try:
            first = next(self._container.decode(self._stream), None)
        except (av.FFmpegError, ValueError) as error:
            self._container.close()
            raise DecodeError(f"cannot read {self._source.path}: {error}") from error
        if first is None or first.pts is None:
            return 0
        return max(0, self._frames_at(first.pts))

    def _slice_frames(self) -> int:
        """Frames in this slice, from the stated length less the priming."""
        stated = self._stream.duration
        if stated is None:
            available = 0
        else:
            available = max(0, self._frames_at(stated) - self._priming)
        start = min(self._source.start_frame, available)
        end = self._source.end_frame
        limit = available if end is None else min(end, available)
        return max(0, limit - start)

    def _frames_at(self, stamp: int) -> int:
        """A timestamp read as a frame index, before the priming is taken off.

        The result counts from the start of the TIMESTAMP timeline, which
        begins one priming ahead of the first sample the decoder hands back.
        """
        base = self._stream.time_base
        if base is None:
            return int(stamp)
        return int(stamp * base * self._sample_rate)

    def _restart(self, absolute: int) -> None:
        """Reopen the decode at or before an absolute frame, discarding state.

        The container really is opened again rather than merely seeked, because
        seeking does not give the decoder back to you clean. Measured: decode
        one packet, seek to the start, decode again: the samples differ
        from a decode that never seeked, by 0.03 of full scale. The overlap the
        codec carries between packets survives both the seek and an explicit
        flush of its buffers. Anywhere with room in front of it the pre-roll
        washes that out, which is why the fault hides on a file whose priming
        FFmpeg skips; at the very start of a track there is no room, so it
        would have reached the speakers.

        Opening the file again costs under a millisecond, measured, against a
        read block worth ninety of them. It buys one path with no stale state
        possible on it, rather than a second path for the case that has none.
        """
        stamp = self._stamp_for(absolute)
        try:
            self._container.close()
            self._container = av.open(self._source.path)
            self._stream = self._container.streams.audio[0]
            self._container.seek(stamp, stream=self._stream, backward=True)
        except (av.FFmpegError, OSError, ValueError, IndexError) as error:
            raise DecodeError(f"cannot seek {self._source.path}: {error}") from error
        self._resampler = av.AudioResampler(
            format=self._format,
            layout=self._stream.codec_context.layout,
            rate=self._sample_rate,
        )
        self._frames = self._container.decode(self._stream)
        self._decoded = []
        self._held = 0
        self._exhausted = False
        self._buffer_at = None

    def _stamp_for(self, absolute: int) -> int:
        """The presentation timestamp standing for an absolute frame index."""
        base = self._stream.time_base
        primed = absolute + self._priming
        if base is None:
            return primed
        return int(primed / (base * self._sample_rate))

    def _discard_to(self, absolute: int) -> None:
        """Decode and throw away everything before the wanted frame."""
        while True:
            self._fill()
            if self._held == 0 or self._buffer_at is None:
                return
            behind = absolute - self._buffer_at
            if behind <= 0:
                return
            self._take(behind)

    def _fill(self) -> None:
        """Decode one more packet into the held buffer, if there is one left."""
        if self._held > 0 or self._exhausted:
            return
        for frame in self._frames:
            if self._buffer_at is None and frame.pts is not None:
                self._buffer_at = self._frames_at(frame.pts) - self._priming
            for block in self._resampled(frame):
                self._keep(block)
            if self._held > 0:
                return
        for block in self._resampled(None):
            self._keep(block)
        self._exhausted = True

    def _resampled(self, frame: object) -> list[np.ndarray]:
        """One decoded frame put into this reader's sample format."""
        assert self._resampler is not None
        try:
            produced = self._resampler.resample(frame)
        except (av.FFmpegError, ValueError) as error:
            raise DecodeError(f"cannot read {self._source.path}: {error}") from error
        return [self._shaped(one.to_ndarray()) for one in produced]

    def _shaped(self, block: np.ndarray) -> np.ndarray:
        """A packed resampler block as (frames, channels)."""
        return block.reshape(-1, self._channels)

    def _keep(self, block: np.ndarray) -> None:
        """Hold a decoded block for a later read."""
        if block.shape[0]:
            self._decoded.append(block)
            self._held += block.shape[0]

    def _take(self, frames: int) -> np.ndarray:
        """Up to `frames` frames out of the buffer, decoding more as needed."""
        collected: list[np.ndarray] = []
        gathered = 0
        while gathered < frames:
            self._fill()
            if self._held == 0:
                break
            block = self._decoded[0]
            room = frames - gathered
            if block.shape[0] <= room:
                collected.append(self._decoded.pop(0))
                gathered += block.shape[0]
                self._held -= block.shape[0]
            else:
                collected.append(block[:room])
                self._decoded[0] = block[room:]
                self._held -= room
                gathered += room
        if self._buffer_at is not None:
            self._buffer_at += gathered
        if not collected:
            return self._empty()
        return np.concatenate(collected, axis=0)

    def _empty(self) -> np.ndarray:
        """A no-frame block of the right shape and type."""
        return np.zeros((0, self._channels), dtype=self._dtype)
