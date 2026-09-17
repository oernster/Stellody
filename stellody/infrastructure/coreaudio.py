"""Opening a CoreAudio output stream on macOS, then reporting what it is.

The Windows module takes the device away from the system mixer. Nothing here
can do that; the difference is measured rather than assumed. PortAudio's
own flags were read on 2026-09-17: `paMacCorePro` is 0x1, which is exactly
`paMacCoreChangeDeviceParameters`; `kAudioDevicePropertyHogMode` is not
exposed by PortAudio at all. So there is no route to sole ownership of a Mac
device through this substrate.

**What IS reachable is the part a listener hears.** Two flags together tell
CoreAudio to run the device at the track's own rate and to refuse the stream
rather than convert: `change_device_parameters` and
`fail_if_conversion_required`. A stream that opens on those terms carries the
file's samples to the hardware unresampled, which is what shared mode cannot
do. Another application playing at the same time is still mixed in, which
Windows exclusive mode prevents and this does not; ARCHITECTURE.md records
that difference rather than leaving the word "exclusive" to carry it.

**Nothing is probed first, deliberately.** `change_device_parameters` may
disturb a device other programs are using "even when you are just querying
the device", in sounddevice's own words, so a probe here would interrupt
somebody else's music to answer a question. The stream is opened instead and a
refusal is the answer, which costs the same and disturbs nothing it did not
have to.

**None of this has been measured on a Mac.** Oliver has no Mac in front of
him and neither has anything here; the flags were read off the built library
on Windows. The report says what was opened, so a Mac that refuses says so on
screen rather than leaving anybody to guess; that report is the
measurement when one is finally taken.
"""

from __future__ import annotations

import sounddevice

from stellody.domain.playback import OutputMode, OutputReport, OutputRequest
from stellody.infrastructure.buffering import buffer_seconds
from stellody.infrastructure.portaudio import (
    DTYPE_BIT_DEPTHS,
    SHARED_DTYPE,
    OutputUnavailableError,
    default_device,
    shared_result,
)

# What a CoreAudio device is fed. Its own format is float, so a float feed is
# the one that reaches the hardware without PortAudio converting on the way;
# an integer sample sits in it exactly, which is why this stays bit perfect.
DIRECT_DTYPE = SHARED_DTYPE
NO_STATED_DEPTH = "the file states no bit depth, so nothing can be bit perfect"


# The two flags this path is, named rather than left inside the call: they
# were read off the built library on 2026-09-17 and they are what the tests
# assert, since the settings object itself cannot be built off a Mac.
DIRECT_FLAGS = ("change_device_parameters", "fail_if_conversion_required")


def direct_settings() -> sounddevice.CoreAudioSettings:
    """Run the device at the track's rate; refuse rather than convert.

    A function rather than an expression inside the opener, because it cannot
    be called anywhere but a Mac: `PaMacCore_SetupStreamInfo` is absent from
    the Windows build of PortAudio, measured on 2026-09-17, so constructing
    one here raises. That makes this the seam a test stands in, which is the
    only way the path around it can be exercised at all.
    """
    return sounddevice.CoreAudioSettings(
        **{name: True for name in DIRECT_FLAGS},
    )


def _open_direct(
    device: int | None, request: OutputRequest
) -> sounddevice.OutputStream:
    """A stream at the track's own rate, with conversion refused."""
    return sounddevice.OutputStream(
        device=device,
        samplerate=request.sample_rate,
        channels=request.channels,
        dtype=DIRECT_DTYPE,
        latency=buffer_seconds(request.sample_rate),
        extra_settings=direct_settings(),
    )


def _open_shared(
    device: int | None, request: OutputRequest
) -> sounddevice.OutputStream:
    """A stream through the mixer, which converts whatever it is given."""
    return sounddevice.OutputStream(
        device=device,
        samplerate=request.sample_rate,
        channels=request.channels,
        dtype=SHARED_DTYPE,
        latency=buffer_seconds(request.sample_rate),
    )


def _shared_result(
    device: int | None, request: OutputRequest, reason: str
) -> tuple[sounddevice.OutputStream, OutputReport, str]:
    """Open the mixer path, recording why it was taken when it was a fallback."""
    try:
        stream = _open_shared(device, request)
    except Exception as error:  # reported, never swallowed
        raise OutputUnavailableError(
            f"no output at {request.sample_rate} Hz: {error}"
        ) from error
    return shared_result(stream, request, reason)


def open_output(
    request: OutputRequest, device: int | None = None
) -> tuple[sounddevice.OutputStream, OutputReport, str]:
    """Open the best stream for `request`, with the report and the feed dtype.

    Raises OutputUnavailableError only when even the mixer path fails, which
    means there is no usable output device at all. That is the contract both
    other modules answer to, so the caller never learns which it reached.
    """
    device = default_device() if device is None else device
    if request.mode is not OutputMode.EXCLUSIVE:
        return _shared_result(device, request, "")
    # Refused here rather than left to the device, so the reason names the
    # file instead of blaming the hardware: a lossy source has no depth to
    # deliver untouched, whatever the stream does with it.
    if not request.states_depth:
        return _shared_result(device, request, NO_STATED_DEPTH)
    # A PortAudio built without CoreAudio support is a fallback like any
    # other refusal: measured on Windows, where the symbol the settings need
    # is simply not in the library, so the settings raise before a device is
    # ever consulted. Saying so beats a Mac user meeting a stack trace.
    try:
        stream = _open_direct(device, request)
    except Exception as error:  # noqa: BLE001 - a refusal is a fallback
        return _shared_result(device, request, str(error))
    report = OutputReport(
        request=request,
        mode=OutputMode.EXCLUSIVE,
        sample_rate=request.sample_rate,
        bit_depth=DTYPE_BIT_DEPTHS[DIRECT_DTYPE],
    )
    return stream, report, DIRECT_DTYPE
