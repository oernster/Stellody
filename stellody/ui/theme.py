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
RADIUS_PX = 4
ROW_HEIGHT_PX = 24


def palette_for(mode: Mode) -> Palette:
    """The palette belonging to an appearance."""
    return PALETTES[mode]


def stylesheet(mode: Mode) -> str:
    """The whole application stylesheet for one appearance.

    Every hover and focus rule is gated on :enabled, so a disabled control
    never lights up under the mouse nor as a skipped focus target. The default
    border is transparent and the same width as the focus ring, so gaining
    focus never reflows the layout.
    """
    colour = palette_for(mode)
    return f"""
    QWidget {{
        background-color: {colour.window};
        color: {colour.text};
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
    QTreeView:enabled:focus, QListView:enabled:focus,
    QTextBrowser:enabled:focus, QLineEdit:enabled:focus {{
        border: {FOCUS_WIDTH_PX}px solid {colour.focus_ring};
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
    QPushButton:enabled:hover {{
        border: {FOCUS_WIDTH_PX}px solid {colour.accent};
    }}
    QPushButton:enabled:focus {{
        border: {FOCUS_WIDTH_PX}px solid {colour.focus_ring};
    }}
    QPushButton:enabled:pressed {{
        background-color: {colour.selection};
    }}
    QPushButton:disabled {{
        background-color: {colour.disabled_surface};
        color: {colour.disabled_text};
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
    QLabel[role="muted"] {{
        color: {colour.text_muted};
    }}
    QLabel[role="warning"] {{
        color: {colour.warning};
    }}
    """
