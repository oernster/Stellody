"""Real WMA, WavPack and AAC files, written for a test and thrown away with it.

The formats here differ from every other one the suite exercises in what
proves them. Nothing in the reference library is a WMA, a WavPack or a raw
AAC, so there is no file somebody owns to measure; what these functions write
is encoded by the same FFmpeg that will decode it. `FORMATS.md` section 1.3
states plainly what that is worth and what it is not: it proves the path
through the walker, the probe and the reader; it proves nothing about what a
Windows Media ripper of 2004 actually wrote.

Each fixture states its sample format rather than letting the encoder choose.
That is NFR-F-TEST-002 and it exists because of a measurement: the WavPack
encoder accepts `u8p`, `s16p`, `s32p` and `fltp` and defaults to the FIRST of
them, so a fixture written without saying which is eight bit. A depth test
against it would then assert eight and pass, proving the opposite of what it
was written to prove.
"""

from __future__ import annotations

import pathlib

import av
import numpy as np
from m4a_support import PACKET_FRAMES, RATE, tone

# What a WMA needs before FFmpeg will open the encoder at all: measured on
# 2026-09-09, `avcodec_open2` for wmav2 returns 22, an invalid argument, until
# a bit rate is stated. Every other encoder here picks its own.
WMA_BIT_RATE = 128000

# The sample formats each encoder is asked for, stated rather than defaulted.
# Measured on 2026-09-09: the WMA and AAC encoders accept `fltp` and nothing
# else, so stating it changes no outcome and is written here anyway, since a
# fixture that does not say what it is encoded at is how the WavPack one came
# to be eight bit. WavPack accepts four formats and defaults to `u8p`, which
# is the whole of that story.
WMA_SAMPLE_FORMAT = "fltp"
AAC_SAMPLE_FORMAT = "fltp"
WAVPACK_DEPTHS = {16: "s16p", 32: "s32p"}

# Tags as FFmpeg spells them on the way in. What each format writes them out
# as is the format's business, which is the point: the probe has to translate
# ASF's names and APEv2's; this is the file that gives it something to
# translate.
#
# A raw AAC takes none of them. Measured on 2026-09-09: an ADTS stream has no
# tag block, so mutagen reads no tags out of one however it was written; such
# a file takes its album from its folder as any untagged file does. Passing
# these to `write_aac` is therefore harmless rather than useful; a test
# asserting a tag off an AAC would be asserting something no `.aac` file can
# hold.
FIXTURE_TAGS = {
    "title": "A widened title",
    "album": "A widened album",
    "artist": "A widened artist",
    "album_artist": "A widened album artist",
    "track": "3/12",
    "disc": "1/2",
    "genre": "Test",
}


def _encode(
    path: pathlib.Path,
    codec: str,
    frames: int,
    sample_format: str | None,
    bit_rate: int | None,
    tags: dict[str, str] | None,
    container_format: str | None = None,
) -> pathlib.Path:
    """One encoded file at `path`, from the same tone every fixture uses."""
    samples = tone(frames)
    container = av.open(str(path), "w", format=container_format)
    try:
        if tags:
            container.metadata.update(tags)
        stream = container.add_stream(codec, rate=RATE)
        stream.layout = "stereo"
        if sample_format is not None:
            stream.format = sample_format
        if bit_rate is not None:
            stream.bit_rate = bit_rate
        for start in range(0, frames, PACKET_FRAMES):
            block = np.ascontiguousarray(samples[:, start : start + PACKET_FRAMES])
            frame = av.AudioFrame.from_ndarray(block, format="fltp", layout="stereo")
            frame.sample_rate = RATE
            for packet in stream.encode(frame):
                container.mux(packet)
        for packet in stream.encode(None):
            container.mux(packet)
    finally:
        container.close()
    return path


def write_wma(
    path: pathlib.Path,
    frames: int = RATE,
    tags: dict[str, str] | None = None,
) -> pathlib.Path:
    """A real WMA, tagged as ASF attributes unless told to carry nothing."""
    return _encode(path, "wmav2", frames, WMA_SAMPLE_FORMAT, WMA_BIT_RATE, tags)


def write_wavpack(
    path: pathlib.Path,
    frames: int = RATE,
    depth: int = 16,
    tags: dict[str, str] | None = None,
) -> pathlib.Path:
    """A real WavPack at a stated depth, tagged as APEv2 items."""
    return _encode(path, "wavpack", frames, WAVPACK_DEPTHS[depth], None, tags)


def write_aac(
    path: pathlib.Path,
    frames: int = RATE,
    tags: dict[str, str] | None = None,
) -> pathlib.Path:
    """A real AAC in the ADTS stream a `.aac` file holds.

    The container is stated rather than left to the suffix, since ADTS is the
    bare stream and nothing in the file itself says so.
    """
    return _encode(
        path, "aac", frames, AAC_SAMPLE_FORMAT, None, tags, container_format="adts"
    )


# Every widened format, by the name its album folder takes, with the writer
# that makes one. Stated here so a test can walk all three without naming any
# of them twice.
WIDENED_WRITERS = {
    "wma": write_wma,
    "wv": write_wavpack,
    "aac": write_aac,
}
