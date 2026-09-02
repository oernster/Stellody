"""Real M4A files, written for a test and thrown away with its temporary folder.

Nothing here is a stand-in. The files these functions write are encoded by the
same library that will decode them, so a test using one exercises the container
parsing, the packet timestamps and the codec exactly as a file off a disk would.

A committed fixture was the alternative and it is worse in two ways: a binary
blob in the tree cannot be read in a review; one file cannot be both the
lossy case and the lossless one. Encoding takes a fraction of a second.

The reference decode is deliberately written against PyAV directly rather than
through `PacketReader`, so a test comparing the two is comparing the reader
against something that does not share its arithmetic. A reader checked against
itself would agree with itself however wrong it was.
"""

from __future__ import annotations

import pathlib

import av
import numpy as np

RATE = 44100
CHANNELS = 2
PACKET_FRAMES = 1024

# Two tones a fifth apart, so left and right differ and a channel swap shows up.
LEFT_HZ = 440.0
RIGHT_HZ = 660.0


def tone(frames: int, rate: int = RATE) -> np.ndarray:
    """A deterministic two channel signal, as (channels, frames) float32."""
    moment = np.arange(frames, dtype=np.float32) / rate
    left = np.sin(2 * np.pi * LEFT_HZ * moment)
    right = np.sin(2 * np.pi * RIGHT_HZ * moment)
    return np.vstack([left, right]).astype(np.float32)


def write_m4a(
    path: pathlib.Path,
    frames: int = RATE,
    codec: str = "aac",
    rate: int = RATE,
) -> pathlib.Path:
    """Encode a real M4A at `path` and hand the path back."""
    samples = tone(frames, rate)
    container = av.open(str(path), "w")
    try:
        stream = container.add_stream(codec, rate=rate)
        stream.layout = "stereo"
        for start in range(0, frames, PACKET_FRAMES):
            block = np.ascontiguousarray(samples[:, start : start + PACKET_FRAMES])
            frame = av.AudioFrame.from_ndarray(block, format="fltp", layout="stereo")
            frame.sample_rate = rate
            for packet in stream.encode(frame):
                container.mux(packet)
        for packet in stream.encode(None):
            container.mux(packet)
    finally:
        container.close()
    return path


def decoded(path: pathlib.Path, rate: int = RATE) -> np.ndarray:
    """Everything in the file, as (frames, channels) float32.

    Written against PyAV rather than against the reader under test, so it is an
    independent answer rather than the same answer twice.
    """
    container = av.open(str(path))
    try:
        stream = container.streams.audio[0]
        resampler = av.AudioResampler(
            format="flt", layout=stream.codec_context.layout, rate=rate
        )
        blocks = [
            output.to_ndarray().reshape(-1, CHANNELS)
            for frame in container.decode(stream)
            for output in resampler.resample(frame)
        ]
        blocks.extend(
            output.to_ndarray().reshape(-1, CHANNELS)
            for output in resampler.resample(None)
        )
    finally:
        container.close()
    return np.concatenate(blocks, axis=0)
