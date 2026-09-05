"""The stylesheet built from Stellody's colours, plus the metrics it needs.

The colours themselves live in `stellody.ui.palette`; this module is how they
reach a widget. Both names are re-exported here because every caller asks the
appearance for both at once, so the split below is an arrangement of this
module's own insides rather than a second thing for anybody to learn.
"""

from __future__ import annotations

from stellody.ui.expanding import HEADING_PAD_PX
from stellody.ui.palette import Mode, Palette, palette_for

__all__ = [
    "FOCUS_WIDTH_PX",
    "LABEL_PAD_PX",
    "RADIUS_PX",
    "ROW_HEIGHT_PX",
    "Mode",
    "Palette",
    "palette_for",
    "stylesheet",
]

FOCUS_WIDTH_PX = 2
LICENCE_FONT_PX = 13
# The search box sits among the tray's buttons, so it is sized against them
# rather than against a dialog's default field.
SEARCH_FONT_PX = 20
RADIUS_PX = 4
# A label that carries its own fill needs its text held off the edge of it,
# else the first letter sits against the corner. Every widget here is painted
# by the blanket QWidget rule, so a label reads as a filled rectangle whether
# or not anybody meant it to; where that rectangle is deliberate, it is given
# this breathing room and the house radius rather than left as a hard box.
LABEL_PAD_PX = 8
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
    /* Each TITLE is a stop, so the ring goes round the one the keyboard is
       on rather than across the whole bar: a bar-wide rule draws a line
       through the empty space past the last menu and says which bar has
       focus rather than which menu a press would open. The bar paints that
       ring itself, on the rectangle Qt reports for the title, taking the
       colour from here so the palette stays its one home. */
    QMenuBar {{
        background-color: {colour.surface};
        border-bottom: 1px solid {colour.border};
    }}
    QMenuBar#RingedMenuBar {{
        qproperty-ringColour: {colour.ring};
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
    QLineEdit#SearchBox {{
        font-size: {SEARCH_FONT_PX}px;
        padding-left: {RADIUS_PX}px;
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
    /* The cover chooser's tiles. A picture is picked rather than merely
       highlighted, so the one picked wears the ring the rest of the
       application wears when something is chosen; the tint alone was too
       quiet to read against a wall of sleeves. Scoped by name, since the
       library's own views are not choosing anything. */
    QListWidget#CoverGrid::item {{
        border: {FOCUS_WIDTH_PX}px solid transparent;
        border-radius: {RADIUS_PX}px;
    }}
    QListWidget#CoverGrid::item:selected {{
        border: {FOCUS_WIDTH_PX}px solid {colour.ring};
        background-color: {colour.selection};
        color: {colour.on_selection};
    }}
    QHeaderView::section {{
        background-color: {colour.surface_alt};
        color: {colour.text_muted};
        border: 0px;
        border-bottom: 1px solid {colour.border};
        padding: 5px 6px;
    }}
    /* Room at the left of the first heading for the open-everything arrow,
       which `expanding.py` draws into it. The width is stated there rather
       than here, so the space kept and the thing drawn in it are one number. */
    QHeaderView::section:first {{
        padding-left: {HEADING_PAD_PX}px;
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
    /* A checkbox is a control and wears the same three states as one. It had
       no rule at all, so Tab stopped on it and nothing on screen said so: the
       one stop in the application a reader could land on and not find.
       The ring goes on the SQUARE rather than round the control, since the
       square is what a checkbox is read as. It cannot be drawn from here:
       naming ::indicator makes Qt take the whole subcontrol over and the tick
       goes with it, measured, while a rule scoped to :focus alone changes
       nothing. So `ringed_check.py` paints it and reads its two colours from
       the two properties below; the padding is what leaves room for it. */
    QCheckBox {{
        border: {FOCUS_WIDTH_PX}px solid transparent;
        border-radius: {RADIUS_PX}px;
        padding: 3px 6px;
        qproperty-ringColour: {colour.ring};
        qproperty-dangerColour: {colour.danger};
    }}
    QCheckBox:disabled {{
        color: {colour.disabled_text};
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
    /* The strip along the bottom is ruled off at BOTH edges, where the tray
       above needs only one: the tray has the window's own edge above it, while
       this has the library over it and the window's edge under it. Two lines
       rather than one is what makes it read as a strip rather than as the
       bottom of the library. */
    QWidget#BottomTray {{
        background-color: {colour.surface};
        border-top: 1px solid {colour.border};
        border-bottom: 1px solid {colour.border};
    }}
    QPushButton#TrayButton {{
        background-color: transparent;
        border: {FOCUS_WIDTH_PX}px solid transparent;
        border-radius: {RADIUS_PX}px;
        padding: 0px;
    }}
    QPushButton#TrayButton:enabled:hover, QPushButton#TrayButton:enabled:focus {{
        border: {FOCUS_WIDTH_PX}px solid {colour.ring};
    }}
    /* A picture button that stays down while what it opened is still acting
       on the library: the filter is the one of these there is. The selection
       colour rather than a border, since the ring belongs to the keyboard and
       two rectangles round one button say nothing about which is which. */
    QPushButton#TrayButton:enabled:checked {{
        background-color: {colour.selection};
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
    QLabel#AlbumTitle, QLabel#AlbumArtist, QLabel#AlbumRatingCaption {{
        padding-left: {LABEL_PAD_PX}px;
        padding-right: {LABEL_PAD_PX}px;
    }}
    /* The title and the artist are two labels reading as one block, so the
       radius goes on the outside of the pair: the top corners on the upper
       one, the bottom corners on the lower. Rounding each of them in full
       would pinch the join between them into an hourglass. */
    QLabel#AlbumTitle {{
        border-top-left-radius: {RADIUS_PX}px;
        border-top-right-radius: {RADIUS_PX}px;
    }}
    QLabel#AlbumArtist {{
        border-bottom-left-radius: {RADIUS_PX}px;
        border-bottom-right-radius: {RADIUS_PX}px;
    }}
    QLabel#AlbumRatingCaption {{
        border-radius: {RADIUS_PX}px;
    }}
    QLabel[role="muted"] {{
        color: {colour.text_muted};
    }}
    QLabel[role="warning"] {{
        color: {colour.warning};
    }}
    """
