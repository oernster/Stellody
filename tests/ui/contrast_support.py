"""Measuring whether one colour can be read against another.

The WCAG relative luminance formula, written out rather than taken from a
package: it is nine lines and the suite gains a dependency it would then have
to trust for the one thing it is checking.

Shared by the two suites that measure a surface of this application, the
progress bar and the results dialog. One instrument rather than two copies,
since two that drifted would have the suites disagreeing about what a ratio
even is while appearing to measure the same thing.
"""

from __future__ import annotations

import colorsys

# What ordinary text is asked to clear, from WCAG 2.1 contrast minimum.
READABLE = 4.5
# What one shape against another is asked to clear, from the same place. Lower
# than writing, since a block of colour is read at a glance rather than letter
# by letter.
DISTINCT = 3
# Half a turn of the colour wheel, which is what two hues opposite each other
# are apart. Used as the bar where two colours have to be told apart while
# both stay readable against one background: a lightness ratio cannot be the
# instrument there, since raising it means driving one of the two towards the
# surface it has to be read against.
OPPOSITE_DEGREES = 180
FULL_TURN_DEGREES = 360
# The sRGB luminance coefficients and the threshold below which a channel is
# linear rather than gamma encoded, both from that same definition.
RED_SHARE = 0.2126
GREEN_SHARE = 0.7152
BLUE_SHARE = 0.0722
LINEAR_BELOW = 0.03928
LINEAR_DIVISOR = 12.92
GAMMA_OFFSET = 0.055
GAMMA_EXPONENT = 2.4
FULL_CHANNEL = 255
# Keeps the ratio finite where one side is black.
FLARE = 0.05
CHANNELS = (0, 2, 4)
CHANNEL_DIGITS = 2


def _channel(value: int) -> float:
    """One channel, taken back to light from the encoding it is written in."""
    share = value / FULL_CHANNEL
    if share <= LINEAR_BELOW:
        return share / LINEAR_DIVISOR
    return ((share + GAMMA_OFFSET) / (1 + GAMMA_OFFSET)) ** GAMMA_EXPONENT


def luminance(colour: str) -> float:
    """How much light a colour carries, by the standard's own weighting."""
    digits = colour.lstrip("#")
    red, green, blue = (
        _channel(int(digits[at : at + CHANNEL_DIGITS], 16)) for at in CHANNELS
    )
    return RED_SHARE * red + GREEN_SHARE * green + BLUE_SHARE * blue


def contrast(one: str, other: str) -> float:
    """The ratio between two colours, brighter over darker."""
    first, second = luminance(one), luminance(other)
    brighter, darker = max(first, second), min(first, second)
    return (brighter + FLARE) / (darker + FLARE)


def hue(colour: str) -> float:
    """Where this colour sits on the wheel, in degrees."""
    digits = colour.lstrip("#")
    red, green, blue = (
        int(digits[at : at + CHANNEL_DIGITS], 16) / FULL_CHANNEL for at in CHANNELS
    )
    return colorsys.rgb_to_hls(red, green, blue)[0] * FULL_TURN_DEGREES


def hues_apart(one: str, other: str) -> float:
    """How far apart two colours are on the wheel, the short way round."""
    apart = abs(hue(one) - hue(other)) % FULL_TURN_DEGREES
    return min(apart, FULL_TURN_DEGREES - apart)
