"""How large the whole interface is drawn, said once for every screen.

Ruled on 2026-09-14: everything is drawn at nine tenths of the size it is
built at. Measured that day, the window cannot be made narrower than 1360
points, all of it the tray under the menus, while a 13 inch 4K panel at 300%
scaling gives Qt 1280 by 752 of room. The tray ran off the right edge; the
strip along the foot sat over the artwork.

One multiplier rather than a hundred retuned constants, because every size in
the application is stated against the others: shrinking the trays alone would
leave the dialogs, the fonts and the album pane at a size chosen beside trays
that are no longer that size. Qt's own global scale moves all of them together.

It is asked for, never imposed. A scale already set in the environment wins,
so somebody who wants a different size can still say so without a build.

Measured under this scale on the same machine: that panel reports 1422 by 836,
while the artwork on it still gets 2.7 real pixels for every point. A screen
at 100% scaling is drawn at 0.9 of a pixel per point instead, which is the
trade this makes.
"""

from __future__ import annotations

from collections.abc import MutableMapping

# Qt's own name for its global multiplier, read once as the application is built.
SCALE_VARIABLE = "QT_SCALE_FACTOR"
INTERFACE_SCALE = 0.9
# The least room the window has to fit, as Qt reported it on 2026-09-14 for a
# 13 inch 4K panel at 300% scaling with the taskbar showing. A 1080p screen at
# 150% scaling gives the same width.
SMALLEST_ROOM_WIDTH_PX = 1280
SMALLEST_ROOM_HEIGHT_PX = 752


def use_interface_scale(environment: MutableMapping[str, str]) -> None:
    """Ask Qt for the interface scale, unless a scale is already asked for.

    Must run before the application is built: Qt reads the variable then and
    never again, so a later call changes nothing and says nothing about it.
    """
    environment.setdefault(SCALE_VARIABLE, str(INTERFACE_SCALE))


def on_screen(length: int) -> float:
    """How long a length the window asks for is on screen, in the screen's points."""
    return length * INTERFACE_SCALE
