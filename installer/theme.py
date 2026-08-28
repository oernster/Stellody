"""The setup program's look: the house layout scale over Stellody's palette.

The installer wears the application's own colours, so this module holds no
colour value of its own; it reads the same Palette the application does, which
keeps every colour in one home. What it adds is the house geometry and type
scale, because a setup program is read at arm's length and the application's
default control sizes are too small for that.
"""

from __future__ import annotations

from stellody.ui.theme import Mode, palette_for, stylesheet

WINDOW_WIDTH_PX = 660
WINDOW_HEIGHT_PX = 620
ICON_PX = 56
DIVIDER_PX = 1
MARGIN_SIDE_PX = 36
MARGIN_TOP_PX = 28
MARGIN_BOTTOM_PX = 24
SECTION_SPACING_PX = 14
HEADER_SPACING_PX = 14
BUTTON_GAP_PX = 10

BASE_FONT_PX = 15
TITLE_FONT_PX = 30
VERSION_FONT_PX = 14
SUBTITLE_FONT_PX = 19
TAGLINE_FONT_PX = 15
PATH_FONT_PX = 14
STATUS_FONT_PX = 15
CHECKBOX_FONT_PX = 15
PRIMARY_FONT_PX = 16
SECONDARY_FONT_PX = 15
INDICATOR_PX = 18
PILL_RADIUS_PX = 22
LICENCE_RADIUS_PX = 16
LICENCE_DIALOG_WIDTH_PX = 760
LICENCE_DIALOG_HEIGHT_PX = 560
LICENCE_FONT_PX = 13


def installer_stylesheet(mode: Mode) -> str:
    """The application's stylesheet plus the setup program's own scale."""
    colour = palette_for(mode)
    return stylesheet(mode) + f"""
    QWidget {{
        font-family: 'Segoe UI';
        font-size: {BASE_FONT_PX}px;
    }}
    QLabel#HeaderTitle {{
        font-size: {TITLE_FONT_PX}px;
        font-weight: 700;
        color: {colour.accent};
    }}
    QLabel#HeaderVersion {{
        font-size: {VERSION_FONT_PX}px;
        color: {colour.text_muted};
    }}
    QLabel#SubTitle {{
        font-size: {SUBTITLE_FONT_PX}px;
        font-weight: 700;
        color: {colour.accent};
    }}
    QLabel#Tagline {{
        font-size: {TAGLINE_FONT_PX}px;
        color: {colour.text_muted};
    }}
    QLabel#InstallPath {{
        font-size: {PATH_FONT_PX}px;
        color: {colour.text_muted};
    }}
    QLabel#StatusLine {{
        font-size: {STATUS_FONT_PX}px;
        color: {colour.text};
    }}
    QFrame#Divider {{
        background: {colour.border};
        border: none;
    }}
    QCheckBox {{
        spacing: 10px;
        font-size: {CHECKBOX_FONT_PX}px;
        color: {colour.text};
    }}
    QCheckBox::indicator {{
        width: {INDICATOR_PX}px;
        height: {INDICATOR_PX}px;
    }}
    QPushButton#LicenceButton, QPushButton#ThemeToggle {{
        background: {colour.surface};
        color: {colour.text};
        padding: 8px 16px;
        border-radius: {LICENCE_RADIUS_PX}px;
        font-weight: 600;
    }}
    QPushButton#PrimaryAction {{
        background: {colour.surface_alt};
        color: {colour.text};
        padding: 12px 28px;
        border-radius: {PILL_RADIUS_PX}px;
        font-size: {PRIMARY_FONT_PX}px;
        font-weight: 700;
        min-width: 150px;
    }}
    QPushButton#SecondaryAction, QPushButton#DangerAction {{
        background: {colour.surface};
        color: {colour.text};
        padding: 12px 22px;
        border-radius: {PILL_RADIUS_PX}px;
        font-size: {SECONDARY_FONT_PX}px;
        font-weight: 600;
    }}
    QPushButton#PrimaryAction:disabled,
    QPushButton#SecondaryAction:disabled,
    QPushButton#DangerAction:disabled {{
        background: {colour.disabled_surface};
        color: {colour.disabled_text};
    }}
    QTextBrowser#LicenceView {{
        font-family: 'Consolas', 'Courier New', monospace;
        font-size: {LICENCE_FONT_PX}px;
    }}
    """


def next_mode(mode: Mode) -> Mode:
    """The appearance the toggle switches to."""
    return Mode.LIGHT if mode is Mode.DARK else Mode.DARK
