"""Which output devices there are; which PortAudio device each one is.

`OUTPUTS.md` is the specification. The system's own list is what a listener
chooses from: Windows' enumeration on Windows (`endpoints.py`, whose order is
what tells two devices of one name apart), Qt's list elsewhere. PortAudio opens
the stream, knows devices by number and name only, so a chosen device is found
among PortAudio's by the domain's rule (`opener_position`) at the moment a
stream is opened. That is after PortAudio's list has been taken again where it
had to be, so a device connected since the application started can be opened.

A device that cannot be found is `OutputRefused`, as is one that will not
open: the transport falls back to the system default and the window says why
(FR-O08).
"""

from __future__ import annotations

import sys
from collections.abc import Callable

import sounddevice
from PySide6.QtMultimedia import QMediaDevices

from stellody.application.playback_ports import OutputRefused
from stellody.domain.outputs import OutputDevice, opener_position
from stellody.domain.playback import OutputReport, OutputRequest
from stellody.infrastructure import output, pulsesink
from stellody.infrastructure.portaudio import OutputUnavailableError

WASAPI = "Windows WASAPI"
NOT_FOUND = "{name} is not among the devices the audio library can open"

# How a stream is opened on a chosen device, else on the system default.
NamedOpener = Callable[
    [OutputRequest, OutputDevice | None],
    tuple[sounddevice.OutputStream, OutputReport, str],
]
# How a player asks which rates its device takes: the device, then whether a
# stream is open on it, which decides whether the answer can be had yet.
NamedRates = Callable[[OutputDevice | None, bool], tuple[int, ...] | None]


def listed_outputs() -> tuple[OutputDevice, ...]:
    """The devices the system can play to, as a listener chooses from them.

    On Windows a failure to ask Windows falls back to Qt's list: the same
    devices in another order, which the matching rule refuses to guess
    between where two share a name, so nothing is opened on the wrong one.
    """
    if sys.platform == output.WINDOWS:
        from stellody.infrastructure import endpoints

        try:
            return endpoints.render_endpoints()
        except OSError:
            return qt_outputs()
    return qt_outputs()


def qt_outputs() -> tuple[OutputDevice, ...]:
    """The output devices as Qt lists them; outputs alone, never inputs."""
    return tuple(
        OutputDevice(
            identity=bytes(device.id().data()).decode(errors="replace"),
            name=device.description(),
        )
        for device in QMediaDevices.audioOutputs()
    )


def portaudio_outputs() -> tuple[tuple[int, str], ...]:
    """PortAudio's output devices, numbered, of the host API streams open on.

    WASAPI on Windows, which is the route both shared and exclusive streams
    take; elsewhere whichever host API PortAudio's own default output uses.
    """
    apis = sounddevice.query_hostapis()
    if sys.platform == output.WINDOWS:
        wanted = next(at for at, api in enumerate(apis) if api["name"] == WASAPI)
    else:
        wanted = sounddevice.query_devices(kind="output")["hostapi"]
    return tuple(
        (number, device["name"])
        for number, device in enumerate(sounddevice.query_devices())
        if device["hostapi"] == wanted and device["max_output_channels"] > 0
    )


def portaudio_number(device: OutputDevice) -> int:
    """Which PortAudio device `device` is. Raises `OutputRefused` if unsure."""
    known = portaudio_outputs()
    position = opener_position(
        listed_outputs(), device, tuple(name for _, name in known)
    )
    if position is None:
        raise OutputRefused(NOT_FOUND.format(name=device.name))
    return known[position][0]


def open_named(
    request: OutputRequest, device: OutputDevice | None = None
) -> tuple[sounddevice.OutputStream, OutputReport, str]:
    """Open a stream on `device`, else on the system default.

    Two routes to one device, chosen by platform in `pulsesink.sink_route`:
    Windows and macOS find it in PortAudio's own list by name, while a machine
    playing through a sound server names its sink instead (Amendment 6). A
    named device that will not open at all is a refusal rather than the end of
    the music; the default failing stays what it always was.
    """
    if device is None:
        return output.open_output(request, None)
    sink = pulsesink.sink_route(device)
    if sink is None:
        return _opened(request, portaudio_number(device))
    with pulsesink.chosen_sink(device.identity):
        return _opened(request, sink)


def _opened(
    request: OutputRequest, number: int
) -> tuple[sounddevice.OutputStream, OutputReport, str]:
    """Open on PortAudio device `number`; a failure to open is a refusal."""
    try:
        return output.open_output(request, number)
    except OutputUnavailableError as error:
        raise OutputRefused(str(error)) from error


def named_rates(
    device: OutputDevice | None, _stream_open: bool = False
) -> tuple[int, ...] | None:
    """Which rates `device` takes exclusively; None where that is unknown."""
    if device is None:
        return output.exclusive_rates(None)
    sink = pulsesink.sink_route(device)
    if sink is not None:
        return output.exclusive_rates(sink)
    try:
        return output.exclusive_rates(portaudio_number(device))
    except OutputRefused:
        return None
