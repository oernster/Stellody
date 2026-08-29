"""Colour tokens and the stylesheet built from them.

This is the only module in Stellody that holds a colour value. Every widget
takes its colour from a token here, so the palette can be read, judged and
changed in one place. The accent is drawn from the application artwork, which
runs from deep navy into a bright blue.
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
    switch_on="#ffe135",
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
    switch_on="#ffe135",
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

FOCUS_WIDTH_PX = 2
LICENCE_FONT_PX = 13
RADIUS_PX = 4
ROW_HEIGHT_PX = 24
HAIRLINE_PX = 1
HALF = 2

# The volume slider. The handle carries an outline in the window colour, so it
# reads against the accent below it and against the empty groove above it in
# both appearances without either being named per mode. The overhang is
# negative so the handle sits wider than the channel it runs in.
SLIDER_GROOVE_PX = 6
SLIDER_HANDLE_PX = 18
SLIDER_HANDLE_RADIUS_PX = SLIDER_HANDLE_PX // HALF
SLIDER_HANDLE_OVERHANG_PX = -(SLIDER_HANDLE_PX - SLIDER_GROOVE_PX) // HALF


def palette_for(mode: Mode) -> Palette:
    """The palette belonging to an appearance."""
    return PALETTES[mode]


def stylesheet(mode: Mode) -> str:
    """The whole application stylesheet for one appearance.

    Three ring states and no others: an enabled control shows no ring at rest,
    a green one while hovered or focused; a disabled one shows a permanent red
    ring. The brand accent is never a ring; it carries meaning of its own.
    Every rule is gated on :enabled; the default border is transparent at the
    ring's own width, so gaining a ring never reflows the layout.

    Rings belong to CONTROLS. An item view is pointed into rather than at; its
    current row already says where the reader is, so it takes no ring in
    any state.
    """
    colour = palette_for(mode)
    return f"""
    QWidget {{
        background-color: {colour.window};
        color: {colour.text};
        outline: none;
    }}
    QMainWindow::separator {{
        background-color: {colour.border};
        width: 1px;
        height: 1px;
    }}
    QMenuBar {{
        background-color: {colour.surface};
        border-bottom: 1px solid {colour.border};
    }}
    QMenuBar::item {{
        padding: 4px 10px;
        background: transparent;
    }}
    QMenuBar::item:selected {{
        background-color: {colour.selection};
        color: {colour.on_selection};
    }}
    QMenu {{
        background-color: {colour.surface};
        border: 1px solid {colour.border};
        padding: 4px;
    }}
    QMenu::item {{
        padding: 5px 22px 5px 22px;
    }}
    QMenu::item:selected {{
        background-color: {colour.selection};
        color: {colour.on_selection};
    }}
    QMenu::item:disabled {{
        color: {colour.disabled_text};
    }}
    QTreeView, QListView, QTextBrowser, QLineEdit {{
        background-color: {colour.surface};
        alternate-background-color: {colour.surface_alt};
        border: {FOCUS_WIDTH_PX}px solid transparent;
        border-radius: {RADIUS_PX}px;
        selection-background-color: {colour.selection};
        selection-color: {colour.on_selection};
    }}
    /* An item view rings in NO state. Its current row is the indicator, so a
       rectangle round the whole view outlines everything while selecting
       nothing, which is what a click on the empty space below the last row
       used to do. QTreeView and QListView deliberately gain no rule here. */
    QTextBrowser:enabled:focus {{
        border: {FOCUS_WIDTH_PX}px solid {colour.ring};
    }}
    QLineEdit:enabled:hover, QLineEdit:enabled:focus {{
        border: {FOCUS_WIDTH_PX}px solid {colour.ring};
    }}
    QLineEdit:disabled, QTextBrowser:disabled {{
        border: {FOCUS_WIDTH_PX}px solid {colour.danger};
    }}
    /* A licence is hard wrapped for a fixed pitch font, so it is drawn in
       one. In a proportional face every line falls short of the widest by a
       different amount, which reads as a dialog wider than its own text. */
    QTextBrowser#LicenceView {{
        font-family: 'Consolas', 'Courier New', monospace;
        font-size: {LICENCE_FONT_PX}px;
    }}
    QTreeView::item {{
        padding: 2px 4px;
    }}
    QHeaderView::section {{
        background-color: {colour.surface_alt};
        color: {colour.text_muted};
        border: 0px;
        border-bottom: 1px solid {colour.border};
        padding: 5px 6px;
    }}
    QPushButton {{
        background-color: {colour.surface_alt};
        color: {colour.text};
        border: {FOCUS_WIDTH_PX}px solid transparent;
        border-radius: {RADIUS_PX}px;
        padding: 5px 14px;
    }}
    QPushButton:enabled:hover, QPushButton:enabled:focus {{
        border: {FOCUS_WIDTH_PX}px solid {colour.ring};
    }}
    QPushButton:enabled:pressed {{
        background-color: {colour.selection};
    }}
    /* Disabled is a permanent red ring, not a hover reaction: the border IS
       the state, readable at a glance as present but inert. */
    QPushButton:disabled {{
        background-color: {colour.disabled_surface};
        color: {colour.disabled_text};
        border: {FOCUS_WIDTH_PX}px solid {colour.danger};
    }}
    QWidget#Tray {{
        background-color: {colour.surface};
        border-bottom: 1px solid {colour.border};
    }}
    QPushButton#TrayButton {{
        background-color: transparent;
        border: {FOCUS_WIDTH_PX}px solid transparent;
        border-radius: {RADIUS_PX}px;
        padding: 0px;
    }}
    QPushButton#TrayButton:checked {{
        background-color: {colour.switch_on};
    }}
    QPushButton#TrayButton:enabled:hover, QPushButton#TrayButton:enabled:focus {{
        border: {FOCUS_WIDTH_PX}px solid {colour.ring};
    }}
    QPushButton#TrayButton:disabled {{
        border: {FOCUS_WIDTH_PX}px solid {colour.danger};
    }}
    QStatusBar {{
        background-color: {colour.surface};
        border-top: 1px solid {colour.border};
        color: {colour.text_muted};
    }}
    QProgressBar {{
        background-color: {colour.surface_alt};
        border: 1px solid {colour.border};
        border-radius: {RADIUS_PX}px;
        text-align: center;
        color: {colour.text_muted};
    }}
    QProgressBar::chunk {{
        background-color: {colour.accent};
        border-radius: {RADIUS_PX - 1}px;
    }}
    QScrollBar:vertical, QScrollBar:horizontal {{
        background-color: {colour.window};
        border: 0px;
    }}
    QScrollBar::handle:vertical, QScrollBar::handle:horizontal {{
        background-color: {colour.border};
        border-radius: {RADIUS_PX}px;
        min-height: 28px;
        min-width: 28px;
    }}
    QScrollBar::add-line, QScrollBar::sub-line {{
        height: 0px;
        width: 0px;
    }}
    QFrame#TraySeparator {{
        background-color: {colour.border};
        border: 0px;
    }}
    QFrame#VolumePopup {{
        background-color: {colour.surface};
        border: {HAIRLINE_PX}px solid {colour.border};
        border-radius: {RADIUS_PX}px;
    }}
    QSlider#Volume {{
        background-color: transparent;
        border: {FOCUS_WIDTH_PX}px solid transparent;
        border-radius: {RADIUS_PX}px;
    }}
    QSlider#Volume:enabled:focus {{
        border: {FOCUS_WIDTH_PX}px solid {colour.ring};
    }}
    QSlider#Volume::groove:vertical {{
        background-color: {colour.window};
        border: {HAIRLINE_PX}px solid {colour.border};
        border-radius: {RADIUS_PX}px;
        width: {SLIDER_GROOVE_PX}px;
    }}
    QSlider#Volume::add-page:vertical {{
        background-color: {colour.accent};
        border-radius: {RADIUS_PX}px;
    }}
    QSlider#Volume::sub-page:vertical {{
        background-color: transparent;
    }}
    QSlider#Volume::handle:vertical {{
        background-color: {colour.text};
        border: {FOCUS_WIDTH_PX}px solid {colour.window};
        border-radius: {SLIDER_HANDLE_RADIUS_PX}px;
        height: {SLIDER_HANDLE_PX}px;
        margin: 0px {SLIDER_HANDLE_OVERHANG_PX}px;
    }}
    QLabel[role="muted"] {{
        color: {colour.text_muted};
    }}
    QLabel[role="warning"] {{
        color: {colour.warning};
    }}
    """
