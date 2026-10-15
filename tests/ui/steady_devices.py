"""An output watcher that asks the machine nothing about its sound devices.

A window built the way the application builds it asks the real device which
rates it takes exclusively, which enables the exclusive switch and so decides
whether that switch is a stop in the ring; it also lists the real devices. A
test reading either answered for whatever hardware was on, off or the default
when it ran. A test never depends on that (Oliver's ruling), so every window a
test builds is handed this watcher instead, with one device and fixed answers.
"""

from __future__ import annotations

from stellody.domain.outputs import OutputDevice
from stellody.infrastructure.output_devices import OutputDevices

SPEAKERS = OutputDevice(identity="speakers", name="Speakers")
# A device taking the common rates exclusively, so the switch is offered.
EXCLUSIVE_RATES = (44100, 48000, 96000, 192000)


def steady_devices() -> OutputDevices:
    """A watcher with one device and fixed answers about it."""
    return OutputDevices(
        refresh=lambda: None,
        default_id=lambda: SPEAKERS.identity.encode(),
        rates=lambda _device: EXCLUSIVE_RATES,
        output_ids=lambda: (SPEAKERS.identity.encode(),),
        listing=lambda: (SPEAKERS,),
    )
