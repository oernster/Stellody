"""The transport's half of the equalizer: hold the curve, hand it to the device.

The transport keeps the curve for the same reason it keeps the volume: one
chosen before anything is loaded still has to apply to whatever is loaded next;
the device is the only thing that can act on it.
"""

from __future__ import annotations

from transport_support import FakePlayer

from stellody.application.transport import Transport
from stellody.domain.equalising import Equalisation

LIFT_DB = 4.0


def test_a_new_transport_shapes_nothing() -> None:
    """A fresh install plays the file as it is until somebody says otherwise."""
    transport = Transport(FakePlayer())
    assert transport.equalisation == Equalisation()
    assert transport.equalisation.flat is True


def test_the_curve_reaches_the_device() -> None:
    """The device is the only thing that can act on it."""
    player = FakePlayer()
    transport = Transport(player)
    curve = Equalisation(enabled=True).with_band(3, LIFT_DB)

    transport.set_equalisation(curve)

    assert transport.equalisation == curve
    assert player.equalisation == curve


def test_a_curve_chosen_before_anything_is_loaded_is_still_held() -> None:
    """Which is what lets it apply to whatever is opened next."""
    player = FakePlayer()
    transport = Transport(player)
    curve = Equalisation(enabled=True).with_band(0, LIFT_DB)
    transport.set_equalisation(curve)

    assert transport.equalisation == curve, "nothing loaded is not a reason to forget"
