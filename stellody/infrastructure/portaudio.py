"""Opening an output stream through PortAudio, on any platform.

PortAudio is the substrate every output here sits on. WASAPI is one host API
within it and keeps its own module beside this one, because exclusive mode is a
Windows idea carrying Windows measurements. This module is what is left once
that is taken away: the vocabulary both share, plus the mixer path that exists
everywhere.

The shared vocabulary lives HERE rather than in the Windows module; the
Windows module reads it from here. The direction matters: a host API is a
specialisation of the substrate, so the substrate cannot be the thing that
imports it. A value with two homes is a value with two answers.

**This path offers no exclusive mode; that is a statement about the route
rather than about the machines.** A system mixer owns the device on macOS and
on Linux exactly as one does on Windows. Reaching past it means a different
interface on each: CoreAudio's own on the Mac, ALSA addressing the hardware
directly on Linux. Neither is reachable through the settings object a stream is
opened with here; inside a Flatpak the sandbox hands over a sound socket
rather than a device at all, so there is nothing to take exclusively. A request
for exclusive mode is therefore answered with the mixer path and a reason
saying why, which is the answer a Windows device refusing exclusive mode
already gets. Nothing claims to be bit perfect that is not.
"""

from __future__ import annotations

import sounddevice

from stellody.domain.playback import (
    OutputMode,
    OutputReport,
    OutputRequest,
    PlaybackError,
)

# What a mixer stream is fed in; what that is worth in bits. Both paths
# report the same thing for the same reason: the mixer converts whatever it is
# given, so the depth reaching the hardware is the mixer's rather than the
# file's.
SHARED_DTYPE = "float32"
DTYPE_BIT_DEPTHS = {"int16": 16, "int32": 32, "float32": 32}
MIXER_BIT_DEPTH = DTYPE_BIT_DEPTHS[SHARED_DTYPE]

NO_EXCLUSIVE_HERE = "this platform reaches the device through its mixer only"


class OutputUnavailableError(PlaybackError):
    """Raised when no stream at all could be opened for a request."""


def default_device() -> int | None:
    """Which device to open; None means PortAudio's own default.

    The Windows module has to name its host API, because sounddevice's global
    default resolves through MME there and an MME stream refuses WASAPI
    settings outright. Nothing is being asked for by name here, so there is
    nothing to resolve: the default is whatever PortAudio already chose, which
    on a desktop is whatever the system is currently playing through.
    """
    return None


def open_shared(device: int | None, request: OutputRequest) -> sounddevice.OutputStream:
    """A stream through the system mixer, which converts to reach the device.

    No settings object is passed at all. One belongs to a host API, so handing
    a WASAPI object to CoreAudio or ALSA is the same fault the Windows module
    records in reverse.
    """
    return sounddevice.OutputStream(
        device=device,
        samplerate=request.sample_rate,
        channels=request.channels,
        dtype=SHARED_DTYPE,
    )


def shared_result(
    stream: sounddevice.OutputStream, request: OutputRequest, reason: str
) -> tuple[sounddevice.OutputStream, OutputReport, str]:
    """The report for a mixer stream, with the reason it was the one opened.

    Built here so both platforms describe the same stream the same way. An
    empty reason means the mixer was what was asked for rather than what was
    left. A reason means something was refused; it says what.
    """
    report = OutputReport(
        request=request,
        mode=OutputMode.SHARED,
        sample_rate=request.sample_rate,
        bit_depth=MIXER_BIT_DEPTH,
        fallback_reason=reason,
    )
    return stream, report, SHARED_DTYPE


def open_output(
    request: OutputRequest, device: int | None = None
) -> tuple[sounddevice.OutputStream, OutputReport, str]:
    """Open the mixer stream for `request`, with its report and feed dtype.

    Raises OutputUnavailableError when even the mixer path fails, which means
    there is no usable output device at all. That is the same contract the
    Windows module answers to, so the caller never learns which it reached.
    """
    device = default_device() if device is None else device
    reason = NO_EXCLUSIVE_HERE if request.mode is OutputMode.EXCLUSIVE else ""
    try:
        stream = open_shared(device, request)
    except Exception as error:  # reported, never swallowed
        raise OutputUnavailableError(
            f"no output at {request.sample_rate} Hz: {error}"
        ) from error
    return shared_result(stream, request, reason)
