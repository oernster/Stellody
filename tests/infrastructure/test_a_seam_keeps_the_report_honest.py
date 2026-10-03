"""A gapless follower is refused when it would not be reported as it plays.

Found by the audit of 2026-10-03. The report describing the open stream is built
once, when a track is opened; a follower runs on inside the same stream, so it
inherits that report. The engine took a follower on its rate and channel count
alone, so a 16 bit FLAC said bit perfect all through the Ogg Vorbis after it,
then through a 24 bit FLAC cut to 16 bits by a device taking nothing deeper.

A follower must now also state the same depth (nought being no depth at all,
which is what a lossy file states) and hold the same kind of sample. One that
does not is refused, so it opens as a new stream with a report of its own.
"""

from __future__ import annotations

import numpy as np
import soundfile
from device_support import A_DEVICE, CheckingStream, stand_in_device

from stellody.domain.playback import OutputMode, OutputRequest
from stellody.domain.track import TrackSource
from stellody.infrastructure import wasapi
from stellody.infrastructure.audio import WasapiPlayback

RATE = 44100
FRAMES = 4410
CHANNELS = 2
CD_DEPTH = 16
# The reference hardware: exclusive at 16 bit alone.
SIXTEEN_ONLY = ("int16",)
EVERY_TYPE = wasapi.CANDIDATE_DTYPES
# What a probe states for each of the files below.
STATED = {"PCM_16": 16, "PCM_24": 24, "PCM_32": 32, "FLOAT": 32}
QUIET = 0.25


def _file(tmp_path, name: str, subtype: str, kind: str = "WAV") -> str:
    """A short quiet file of this subtype."""
    path = tmp_path / name
    samples = np.full((FRAMES, CHANNELS), QUIET)
    soundfile.write(str(path), samples, RATE, subtype=subtype, format=kind)
    return str(path)


def _opener(request: OutputRequest, _device: object):
    """The real WASAPI module, standing in front of a stand-in device."""
    return wasapi.open_output(request, A_DEVICE)


def _opened(monkeypatch, path: str, depth: int, takes: tuple[str, ...]):
    """A player holding `path` exclusively on a device taking these types."""
    streams: list[CheckingStream] = []
    stand_in_device(monkeypatch, streams, takes)
    player = WasapiPlayback(opener=_opener)
    request = OutputRequest(
        sample_rate=RATE, bit_depth=depth, mode=OutputMode.EXCLUSIVE
    )
    player.load(TrackSource(path=path), request)
    return player


def test_a_lossy_file_does_not_follow_a_lossless_one(tmp_path, monkeypatch) -> None:
    """16 bit FLAC then Ogg Vorbis: the Ogg opens on its own report."""
    first = _file(tmp_path, "one.flac", "PCM_16", "FLAC")
    lossy = _file(tmp_path, "two.ogg", "VORBIS", "OGG")
    player = _opened(monkeypatch, first, CD_DEPTH, SIXTEEN_ONLY)
    assert player.queue_next(TrackSource(path=lossy)) is False
    player.stop()


def test_a_deeper_file_does_not_follow_on_a_sixteen_bit_device(
    tmp_path, monkeypatch
) -> None:
    """16 bit then 24 bit: the 24 would be cut to 16 under the 16's report."""
    first = _file(tmp_path, "one.flac", "PCM_16", "FLAC")
    deeper = _file(tmp_path, "two.flac", "PCM_24", "FLAC")
    player = _opened(monkeypatch, first, CD_DEPTH, SIXTEEN_ONLY)
    assert player.queue_next(TrackSource(path=deeper)) is False
    player.stop()


def test_a_float_file_does_not_follow_an_integer_one(tmp_path, monkeypatch) -> None:
    """Both state 32 bits; only one of them reaches the stream exactly."""
    first = _file(tmp_path, "one.wav", "PCM_32")
    floating = _file(tmp_path, "two.wav", "FLOAT")
    player = _opened(monkeypatch, first, STATED["PCM_32"], EVERY_TYPE)
    assert player.queue_next(TrackSource(path=floating)) is False
    player.stop()


def test_a_file_of_the_same_kind_still_follows(tmp_path, monkeypatch) -> None:
    """The control: two 16 bit FLACs at one rate still join without a gap."""
    first = _file(tmp_path, "one.flac", "PCM_16", "FLAC")
    second = _file(tmp_path, "two.flac", "PCM_16", "FLAC")
    player = _opened(monkeypatch, first, CD_DEPTH, SIXTEEN_ONLY)
    assert player.queue_next(TrackSource(path=second)) is True
    player.stop()
