"""The transport's half of the visualiser: say who is watching, pass on what is seen.

The transport holds whether anything is watching for the same reason it holds
the curve: the device is the only thing that can measure, the only thing that
can be told to stop. What comes back is read through rather than kept,
since a measurement that is one frame old is already the wrong one.
"""

from __future__ import annotations

from transport_support import FakePlayer

from stellody.application.transport import Transport
from stellody.domain.equalising import BAND_COUNT
from stellody.domain.spectrum import FULL, SILENT_BANDS

LOUD = (FULL,) * BAND_COUNT


def test_a_new_transport_is_watching_nothing() -> None:
    """Off costs nothing, so off is what a fresh install measures."""
    transport = Transport(FakePlayer())
    assert transport.visualising is False
    assert transport.levels == SILENT_BANDS


def test_saying_somebody_is_watching_reaches_the_device() -> None:
    """The device is the only thing that can decide not to measure."""
    player = FakePlayer()
    transport = Transport(player)

    transport.set_visualising(True)

    assert transport.visualising is True
    assert player.visualising is True


def test_saying_nobody_is_watching_reaches_it_too() -> None:
    """Turning it back off is the half that keeps the bargain."""
    player = FakePlayer()
    transport = Transport(player)
    transport.set_visualising(True)

    transport.set_visualising(False)

    assert transport.visualising is False
    assert player.visualising is False


def test_the_measurement_is_read_through_rather_than_kept() -> None:
    """Held anywhere it would be stale by the time anything drew it."""
    player = FakePlayer()
    transport = Transport(player)
    player.measured = LOUD

    assert transport.levels == LOUD

    player.measured = SILENT_BANDS
    assert transport.levels == SILENT_BANDS, "the last answer was not kept"
