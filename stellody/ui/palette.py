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
    # What a search flashes behind the track it hit. A role of its own rather
    # than `selection`, because the hit track is selected at the same moment,
    # so a flash in the selection colour would show nothing at all. The text
    # keeps its own colour throughout, so this has to be readable behind it:
    # banana yellow carries the dark writing of the light appearance at 13.33
    # to 1, while the dark appearance needs a deep amber to carry its light
    # writing, measured at 5.10 to 1.
    found: str
    # A star that has been given, against the panel the rating sits in. Its own
    # role, because a shape this small needs a colour that carries at twenty
    # pixels rather than a wash meant to fill a whole button.
    # Measured against `surface_alt`: 4.44 to 1 in the light appearance, 9.28
    # to 1 in the dark one, where a graphic of this kind asks for 3.
    star: str
    # A progress bar carries writing across BOTH halves of itself, so three
    # colours have to settle together: the text must read against the fill AND
    # against the groove, while the fill must still be told apart from that
    # groove. The bar used the accent as its fill and the muted text over it,
    # which measured 1.29 to 1 in the light appearance and 1.32 to 1 in the
    # dark one: a smudge rather than a sentence.
    #
    # The groove is a role of its own rather than `surface_alt`, because with
    # that surface fixed the three constraints have almost no solution left:
    # every fill readable enough for the text sat within 2.5 to 1 of the
    # groove. Measured for these, in order text on groove, text on fill, fill
    # on groove: light 17.42, 5.54 and 3.14; dark 16.81, 4.82 and 3.48. The
    # bar is 4.5 for the writing and 3 for one shape against another.
    #
    # Re-measured on 2026-09-07 after the dark fill was taken down and its
    # writing taken up to plain white, reported as still not bright enough at
    # the near-white it had: text on fill 8.85, text on groove 18.68.
    progress_groove: str
    progress_fill: str
    # A line round the filled part, which is what tells it from the groove now
    # that the fill is dark. Reported on 2026-09-07: the white writing did not
    # carry over the fill, measured at 4.82 to 1 in the dark appearance, which
    # clears the bar and still reads as grey on blue. Taking the fill down to
    # #24478f lifts that to 7.96; the cost is that the fill then sits at 2.11
    # against a groove which is nearly black, so the two shapes could no
    # longer be told apart by lightness alone.
    #
    # So the boundary is drawn rather than inferred. Measured for the edge, in
    # order against the fill then against the groove: 3.64 and 7.68 in the dark
    # appearance. The light appearance keeps a fill its groove already separates
    # (3.14 to 1 against white), so its edge is there to mark the boundary
    # rather than to carry it: 2.50 against the fill, 7.84 against the groove.
    progress_edge: str
    on_progress: str
    # The two kinds of artist a discovery run turns up, which mean opposite
    # things: a source artist is somebody the library already holds who is
    # missing records, while a candidate artist is somebody it holds nothing
    # by. Blue for the one already there, amber for the one that is not; two
    # hues rather than two shades of one, so the pair survives a reader who
    # cannot separate red from green. FR-D34.
    #
    # Measured against the surface a results row sits on, in order surface
    # then the alternating surface: source 7.59 and 6.72 in the light
    # appearance, 8.21 and 7.41 in the dark one; candidate 7.03 and 6.22
    # light, 9.32 and 8.41 dark. The bar is 4.5, since these are names being
    # read rather than shapes being told apart. NFR-USE-002.
    source_artist: str
    candidate_artist: str
    on_accent: str
    selection: str
    on_selection: str
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
    found="#ffe135",
    star="#b45309",
    progress_groove="#ffffff",
    progress_fill="#5c93de",
    progress_edge="#14509f",
    on_progress="#141a26",
    source_artist="#0f4fb0",
    candidate_artist="#8a4708",
    on_accent="#ffffff",
    selection="#d6e2fb",
    on_selection="#101725",
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
    found="#7a5f14",
    star="#fbbf24",
    progress_groove="#0d1220",
    progress_fill="#24478f",
    progress_edge="#74a6ff",
    on_progress="#ffffff",
    source_artist="#8ab4ff",
    candidate_artist="#f5b342",
    on_accent="#08101f",
    selection="#213158",
    on_selection="#eef3ff",
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
