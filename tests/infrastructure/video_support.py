"""Real M4V files, written for a test and thrown away with its temporary folder.

The same argument as `m4a_support`, which this builds on: a file encoded by the
library that will decode it exercises the container, the packet timestamps and
the codecs exactly as a file off a disk does, where a stand-in exercises the
stand-in. The audio tone comes from there unchanged, so a test comparing the
sound of a video against the sound of an M4A is comparing like with like.

What a video file adds is a second stream in the same container. Every file
written here carries H.264 beside the AAC, which is what every video file in
the reference library carries; the picture is a flat grey that steps one value
per frame, so a frame can be told from its neighbour by reading one pixel.
"""

from __future__ import annotations

import pathlib

import av
import numpy as np
from m4a_support import PACKET_FRAMES, RATE, tone

VIDEO_CODEC = "libx264"
FRAMES_PER_SECOND = 25
WIDTH = 64
HEIGHT = 48
PIXEL_FORMAT = "yuv420p"

# How much the flat grey steps between one picture and the next. Large enough
# to survive the codec, small enough that a second of pictures does not wrap.
GREY_STEP = 8


def grey_for(picture: int) -> int:
    """The value every pixel of picture `n` carries, so a frame names itself."""
    return (picture * GREY_STEP) % 256


def write_m4v(
    path: pathlib.Path,
    frames: int = RATE,
    rate: int = RATE,
    fps: int = FRAMES_PER_SECOND,
) -> pathlib.Path:
    """Encode a real M4V holding both streams at `path`, handing the path back.

    `frames` is a count of AUDIO frames, so the two streams are asked for the
    same duration rather than for a duration each.
    """
    samples = tone(frames, rate)
    pictures = max(1, round(frames / rate * fps))
    container = av.open(str(path), "w")
    try:
        video = container.add_stream(VIDEO_CODEC, rate=fps)
        video.width, video.height, video.pix_fmt = WIDTH, HEIGHT, PIXEL_FORMAT
        audio = container.add_stream("aac", rate=rate)
        audio.layout = "stereo"
        for picture in range(pictures):
            flat = np.full((HEIGHT, WIDTH, 3), grey_for(picture), dtype=np.uint8)
            for packet in video.encode(
                av.VideoFrame.from_ndarray(flat, format="rgb24")
            ):
                container.mux(packet)
        for start in range(0, frames, PACKET_FRAMES):
            block = np.ascontiguousarray(samples[:, start : start + PACKET_FRAMES])
            frame = av.AudioFrame.from_ndarray(block, format="fltp", layout="stereo")
            frame.sample_rate = rate
            for packet in audio.encode(frame):
                container.mux(packet)
        for stream in (video, audio):
            for packet in stream.encode(None):
                container.mux(packet)
    finally:
        container.close()
    return path
