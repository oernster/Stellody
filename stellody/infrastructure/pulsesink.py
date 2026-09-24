"""Sending the music to one sound server sink, through PortAudio's `pulse`.

`OUTPUTS.md` section 1.3 and Amendment 6 are the specification. On Linux the
two lists never meet by name: Qt reads the sound server and calls a device
`Px7 S3`, while PortAudio was built against ALSA and calls what it can see
`default`, `pulse` and `HD-Audio Generic: HDMI 0 (hw:0,3)`. Measured inside the
installed Flatpak on 2026-09-19: not one Qt name appeared in PortAudio's list,
so every chosen device was refused and the music stayed where the system
default sends it, whatever the listener picked.

What the two lists DO share is identity. Qt's id for a device here is the
sink's own name (`bluez_output.EC:66:D1:CC:5A:F0`), which is the name the sound
server answers to. So a device is addressed rather than matched: the stream is
opened on PortAudio's `pulse` device with `PULSE_SINK` naming the sink; the
sound server then puts it where it was asked to. Measured the same day, in the
Flatpak, by reading which sink the stream landed on: the speaker sink, then the
headphones, then the default with the variable unset, each on demand within one
process.

The variable is set around the open alone and put back afterwards. A sink is
chosen when the stream connects, so a stream already open stays where it is;
that too was measured rather than assumed. A name no sink carries is not an
error either: the stream opens on the system default, which is the fallback
FR-O10 asks for.
"""

from __future__ import annotations

import contextlib
import os
import sys
from collections.abc import Iterator

import sounddevice

from stellody.domain.outputs import OutputDevice
from stellody.infrastructure import output

# The ALSA device every sound server offers; beside it, the variable libpulse
# reads to decide which sink a stream connects to.
PULSE_DEVICE = "pulse"
SINK_VARIABLE = "PULSE_SINK"


def routes_by_sink(platform: str | None = None) -> bool:
    """Whether this platform addresses a device by sink rather than by name.

    Asked of the platform for the same reason `output.open_output` asks it:
    what differs is the interface. Windows and macOS each hand PortAudio a
    device list a listener's own names appear in, so there is a device to
    match; anything else reaches its hardware through a sound server, where
    there is a sink to name instead.
    """
    return (platform or sys.platform) not in (output.WINDOWS, output.MACOS)


def pulse_device() -> int | None:
    """Which PortAudio device is the sound server; None where there is none.

    None is a Linux machine with no sound server running, where ALSA names
    the hardware directly and the by-name match is the right route after all.
    PortAudio's list is taken here, on the way into opening a stream, which is
    the only moment section 2.4 allows it to be taken.
    """
    return next(
        (
            number
            for number, device in enumerate(sounddevice.query_devices())
            if device["name"] == PULSE_DEVICE and device["max_output_channels"] > 0
        ),
        None,
    )


def sink_route(device: OutputDevice, platform: str | None = None) -> int | None:
    """Which PortAudio device addresses `device`; None where this is not it.

    None means the caller should go on matching by name. Three ways to it:
    this platform does not route by sink; the device has no identity to name a
    sink with; there is no sound server to name it to.
    """
    if not routes_by_sink(platform) or not device.identity:
        return None
    return pulse_device()


@contextlib.contextmanager
def chosen_sink(identity: str) -> Iterator[None]:
    """Hold `identity` as the sink to connect to, then put back what was there.

    The variable belongs to the process, so it is held for the open alone
    rather than kept: anything else would quietly move a stream opened later
    for another reason.
    """
    previous = os.environ.get(SINK_VARIABLE)
    os.environ[SINK_VARIABLE] = identity
    try:
        yield
    finally:
        if previous is None:
            os.environ.pop(SINK_VARIABLE, None)
        else:
            os.environ[SINK_VARIABLE] = previous
