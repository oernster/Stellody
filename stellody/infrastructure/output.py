"""Which output module this machine plays through.

One question, answered in one place, so nothing else in the application has to
know there is more than one answer. Both modules behind it present the same
call and hand back the same three things, which is what lets the transport stay
ignorant of the platform it is running on.

The switch is on `sys.platform` rather than on what a device reports, because
what differs is the INTERFACE rather than the hardware: WASAPI exists on
Windows and nowhere else, so asking a Mac whether it has one is asking the
wrong question. Anything neither Windows nor macOS takes the substrate, which
is the safe direction for the rule to fail in: a platform nobody has thought
about plays through its mixer rather than not at all.

Linux is that case DELIBERATELY, not by omission. Ruled out with Oliver on
2026-09-17: the Linux build is a Flatpak, so the sandbox hands over a sound
socket rather than a device and there is nothing to take; outside the sandbox
the answer depends on whether PipeWire will let go, on whether PortAudio was
built against ALSA and on a raw device existing to address, which differs
between distributions and between machines of one distribution. A mode that
worked on some Linux machines and quietly did not on others is worse than one
that says up front that it is not offered. The control says so itself rather
than leaving the reason to a document nobody opens; see `offers_exclusive`.
"""

from __future__ import annotations

import sys
from collections.abc import Callable

from stellody.infrastructure import portaudio

WINDOWS = "win32"
MACOS = "darwin"
# Said to a listener rather than to a developer: it names the platform and it
# names the consequence, because a disabled control with no reason on it reads
# as a fault in the application. The why stays in this module's docstring,
# ruled by Oliver on 2026-09-18: a listener is owed what happens, not the
# packaging argument behind it.
NO_EXCLUSIVE_ON_LINUX = (
    "Exclusive output is not offered on Linux. The music plays through the "
    "system mixer."
)


def offers_exclusive(platform: str | None = None) -> bool:
    """Whether this platform has any route past its own mixer.

    Asked of the platform rather than of a device, because what is missing on
    Linux is the route rather than the hardware. The window asks this once at
    startup and stands the control down where the answer is no.
    """
    return (platform or sys.platform) in (WINDOWS, MACOS)


def exclusive_rates(device: int | None = None) -> tuple[int, ...] | None:
    """Which rates this platform will take exclusively; None where unknown.

    Three answers rather than two, because they are three different
    facts. A tuple is what the device said. An empty tuple is a device
    that will take none, which is worth saying out loud. None is a
    platform that cannot be asked without cost: on a Mac the flags that
    would answer may disturb a device other programs are using, in
    sounddevice's own words, so the question is not asked at all and
    nothing is claimed about the answer.

    Linux answers the empty tuple because the mode is not offered there;
    see the note at the top of this module.
    """
    if sys.platform == WINDOWS:
        from stellody.infrastructure import wasapi

        return wasapi.exclusive_rates(device)
    if sys.platform == MACOS:
        return None
    return ()


# How a player asks which rates its device takes: the device, then whether a
# stream is open on it, which decides whether the answer can be had yet.
Rates = Callable[[int | None, bool], tuple[int, ...] | None]


def asked_afresh(device: int | None, _stream_open: bool) -> tuple[int, ...] | None:
    """Ask the driver every time; for a player built without a device watcher.

    The composition root hands the player `OutputDevices.exclusive_rates`
    instead, which keeps the answer and knows when the device has moved.
    """
    return exclusive_rates(device)


def open_output(*args, **kwargs):
    """Open an output stream through whichever module this platform wants.

    Imported inside the call rather than at module scope, because the Windows
    module names a host API that only exists there. Importing it on a Mac
    costs nothing today and would be a trap the day it reaches for something
    Windows-only at import time.
    """
    if sys.platform == WINDOWS:
        from stellody.infrastructure import wasapi

        return wasapi.open_output(*args, **kwargs)
    if sys.platform == MACOS:
        from stellody.infrastructure import coreaudio

        return coreaudio.open_output(*args, **kwargs)
    return portaudio.open_output(*args, **kwargs)
