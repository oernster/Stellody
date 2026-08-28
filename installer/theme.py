"""The setup program's look: the house shell over Stellody's own palette.

Translated from the reference setup program's stylesheet, so the geometry and
the type scale are the house ones rather than anything invented here. Only the
colours are Stellody's, read from the same Palette the application uses, which
keeps every colour value in one home.

The ring model is the house one and it is not the application's: no ring at
rest, a green ring while an enabled control is hovered or focused and a
permanent rose ring while a control is disabled. So this is a stylesheet in its
own right rather than a layer over the application's, which carries a different
model and would otherwise fight it.
"""

from __future__ import annotations

from stellody.ui.theme import Mode, palette_for

WINDOW_WIDTH_PX = 850
WINDOW_HEIGHT_PX = 770
MARK_PX = 126
TOGGLE_PX = 74
TOGGLE_ICON_PX = 55
CHECK_PX = 24
TRACK_PX = 9
RING_PX = 2

SHELL_MARGIN_SIDE_PX = 26
SHELL_MARGIN_TOP_PX = 22
SHELL_MARGIN_BOTTOM_PX = 18
HEADER_GAP_PX = 13
HEADER_PAD_PX = 15
FOOTER_PAD_PX = 15
FOOTER_GAP_PX = 9
OPTION_GAP_PX = 10
OPTION_SPACING_PX = 11

BASE_FONT_PX = 18
FLOW_FONT_PX = 22
TITLE_FONT_PX = 32
SUB_FONT_PX = 18
HEADING_FONT_PX = 28
INFO_FONT_PX = 16
HINT_FONT_PX = 15
STATUS_FONT_PX = 16
VERDICT_FONT_PX = 44
LICENCE_FONT_PX = 13


GLOW_ALPHA = 0.11
GLOW_CENTRE = -0.08
GLOW_RADIUS = 0.9
GLOW_EDGE = 0.7
HEX_PAIRS = ((1, 3), (3, 5), (5, 7))


def tinted(colour: str, alpha: float) -> str:
    """One palette colour at a given transparency.

    A derivation rather than a second colour value, so the glow can never
    drift away from the accent it is a glow of.
    """
    red, green, blue = (int(colour[start:end], 16) for start, end in HEX_PAIRS)
    return f"rgba({red}, {green}, {blue}, {alpha})"


def installer_stylesheet(mode: Mode) -> str:
    """The whole setup program stylesheet for one appearance."""
    colour = palette_for(mode)
    glow = tinted(colour.accent, GLOW_ALPHA)
    return f"""
    QWidget {{
        background: {colour.window};
        color: {colour.text};
        font-family: 'Segoe UI';
        font-size: {BASE_FONT_PX}px;
    }}
    /* The glow belongs to the window, so everything drawn over it says so
       rather than painting the flat colour back on top of it. */
    QWidget#Shell {{
        background: qradialgradient(
            cx: 0.5, cy: {GLOW_CENTRE}, radius: {GLOW_RADIUS},
            fx: 0.5, fy: {GLOW_CENTRE},
            stop: 0 {glow}, stop: {GLOW_EDGE} {colour.window}
        );
    }}
    QWidget#Pane, QWidget#Body, QWidget#Footer, QLabel, QCheckBox {{
        background: transparent;
    }}
    QLabel#FlowFrom {{
        font-size: {FLOW_FONT_PX}px;
        color: {colour.text_muted};
    }}
    QLabel#FlowArrow {{
        font-size: {FLOW_FONT_PX}px;
        color: {colour.accent};
    }}
    QLabel#FlowTo {{
        font-size: {FLOW_FONT_PX}px;
        font-weight: 700;
    }}
    QLabel#HeaderTitle {{
        font-size: {TITLE_FONT_PX}px;
        font-weight: 700;
    }}
    QLabel#HeaderSub {{
        font-size: {SUB_FONT_PX}px;
        color: {colour.text_muted};
    }}
    QLabel#Heading {{
        font-size: {HEADING_FONT_PX}px;
        font-weight: 700;
    }}
    QLabel#Lead {{
        color: {colour.text_muted};
    }}
    QLabel#Hint {{
        font-size: {HINT_FONT_PX}px;
        color: {colour.text_muted};
    }}
    QLabel#Status {{
        font-size: {STATUS_FONT_PX}px;
        color: {colour.text_muted};
    }}
    QLabel#Verdict {{
        font-size: {VERDICT_FONT_PX}px;
    }}
    QLabel#InfoBox {{
        background: {colour.surface};
        border: 1px solid {colour.border};
        border-radius: 9px;
        padding: 13px 16px;
        font-size: {INFO_FONT_PX}px;
        color: {colour.text_muted};
    }}
    QFrame#Rule {{
        background: {colour.border};
        border: none;
    }}
    QCheckBox {{
        spacing: {OPTION_GAP_PX}px;
        border: {RING_PX}px solid transparent;
        border-radius: 8px;
        padding: 5px 7px;
    }}
    QCheckBox:enabled:hover, QCheckBox:enabled:focus {{
        border-color: {colour.ring};
    }}
    QCheckBox:disabled {{
        border-color: {colour.danger};
        color: {colour.disabled_text};
    }}
    QCheckBox::indicator {{
        width: {CHECK_PX}px;
        height: {CHECK_PX}px;
        border: 1px solid {colour.border};
        border-radius: 5px;
        background: {colour.surface};
    }}
    QCheckBox::indicator:checked {{
        background: {colour.accent};
        border-color: {colour.accent};
    }}
    QCheckBox::indicator:disabled {{
        background: {colour.disabled_surface};
    }}
    QPushButton {{
        background: {colour.surface_alt};
        color: {colour.text};
        border: {RING_PX}px solid transparent;
        border-radius: 9px;
        padding: 11px 22px;
        font-weight: 600;
    }}
    QPushButton:enabled:hover, QPushButton:enabled:focus {{
        border-color: {colour.ring};
    }}
    QPushButton:disabled {{
        border-color: {colour.danger};
        color: {colour.disabled_text};
    }}
    QPushButton#Primary {{
        background: {colour.selection};
        color: {colour.accent};
    }}
    QPushButton#Danger {{
        background: {colour.danger_soft};
        color: {colour.danger};
    }}
    QPushButton#ThemeToggle {{
        background: {colour.surface_alt};
        border-radius: 12px;
        padding: 0px;
        min-width: {TOGGLE_PX}px;
        max-width: {TOGGLE_PX}px;
        min-height: {TOGGLE_PX}px;
        max-height: {TOGGLE_PX}px;
    }}
    QProgressBar {{
        background: {colour.surface_alt};
        border: 1px solid {colour.border};
        border-radius: 5px;
        max-height: {TRACK_PX}px;
        min-height: {TRACK_PX}px;
        text-align: center;
        color: transparent;
    }}
    QProgressBar::chunk {{
        background: {colour.accent};
        border-radius: 4px;
    }}
    QTextBrowser {{
        background: {colour.surface};
        border: 1px solid {colour.border};
        border-radius: 9px;
        color: {colour.text};
        font-family: 'Consolas', 'Courier New', monospace;
        font-size: {LICENCE_FONT_PX}px;
    }}
    QDialog {{
        background: {colour.window};
    }}
    """


def next_mode(mode: Mode) -> Mode:
    """The appearance the toggle switches to."""
    return Mode.LIGHT if mode is Mode.DARK else Mode.DARK
