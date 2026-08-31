"""Every colour Stellody paints, named by role rather than by value.

This is the only module in Stellody that holds a colour value. Every widget
takes its colour from a token here, so the palette can be read, judged and
changed in one place. The accent is drawn from the application artwork, which
runs from deep navy into a bright blue.

Kept apart from the stylesheet that uses it: what a colour IS and where it is
APPLIED are two questions. They change for different reasons; the file holding
both had grown to the point where the line cap said so.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class Mode(StrEnum):
    """The two appearances Stellody offers."""

    LIGHT = "light"
    DARK = "dark"


@dataclass(frozen=True, slots=True)
class Palette:
    """Every colour the interface uses, named by role rather than by value."""

    window: str
    surface: str
    surface_alt: str
    border: str
    text: str
    text_muted: str
    text_dim: str
    accent: str
    accent_hover: str
    switch_on: str
    # What a search flashes behind the track it hit. A role of its own rather
    # than `selection`, because the hit track is selected at the same moment,
    # so a flash in the selection colour would show nothing at all. The text
    # keeps its own colour throughout, so this has to be readable behind it:
    # banana yellow carries the dark writing of the light appearance at 13.33
    # to 1, while the dark appearance needs a deep amber to carry its light
    # writing, measured at 5.10 to 1.
    found: str
    # A star that has been given, against the panel the rating sits in. Its own
    # role rather than `switch_on`, which is a pale wash meant to fill a whole
    # button: a shape this small needs a colour that carries at twenty pixels.
    # Measured against `surface_alt`: 4.44 to 1 in the light appearance, 9.28
    # to 1 in the dark one, where a graphic of this kind asks for 3.
    star: str
    on_accent: str
    selection: str
    on_selection: str
    focus_ring: str
    disabled_surface: str
    disabled_text: str
    warning: str
    ring: str
    danger: str
    danger_soft: str


LIGHT = Palette(
    window="#f4f6fb",
    surface="#ffffff",
    surface_alt="#eef1f8",
    border="#c9d2e3",
    text="#141a26",
    text_muted="#4a5568",
    text_dim="#8a94a6",
    accent="#1b5fd0",
    accent_hover="#1750b3",
    switch_on="#fff5a3",
    found="#ffe135",
    star="#b45309",
    on_accent="#ffffff",
    selection="#d6e2fb",
    on_selection="#101725",
    focus_ring="#1b5fd0",
    disabled_surface="#e7eaf1",
    disabled_text="#a3abb9",
    warning="#a8560a",
    ring="#047857",
    danger="#be123c",
    danger_soft="#ffe4e6",
)

DARK = Palette(
    window="#0d1220",
    surface="#141b2d",
    surface_alt="#1b2438",
    border="#2b3650",
    text="#e6ecf7",
    text_muted="#9aa7c0",
    text_dim="#6b7891",
    accent="#4c8dff",
    accent_hover="#69a1ff",
    switch_on="#fff5a3",
    found="#7a5f14",
    star="#fbbf24",
    on_accent="#08101f",
    selection="#213158",
    on_selection="#eef3ff",
    focus_ring="#4c8dff",
    disabled_surface="#171e2e",
    disabled_text="#4d586e",
    warning="#e0a458",
    ring="#34d399",
    danger="#fb7185",
    danger_soft="#35161f",
)

PALETTES: dict[Mode, Palette] = {Mode.LIGHT: LIGHT, Mode.DARK: DARK}


def palette_for(mode: Mode) -> Palette:
    """The palette belonging to an appearance."""
    return PALETTES[mode]
