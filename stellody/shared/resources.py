"""Locating the assets bundled beside the application.

The same code runs from a source checkout, from a compiled bundle and from a
Flatpak, so the assets directory is searched for rather than assumed.
"""

from __future__ import annotations

import pathlib
import sys

ASSETS_DIR = "assets"
WINDOW_ICON = "stellody_icon_256.png"
APPLICATION_ICON = "stellody.ico"
MODEL_LICENCE = "LICENSE-GPL-3.0.txt"
UI_LICENCE = "LICENSE-LGPL-3.0.txt"
LIGHT_MODE_ICON = "light-mode.png"
DARK_MODE_ICON = "dark-mode.png"
CHOOSE_FOLDER_ICON = "choose-folder.png"
RESCAN_ICON = "rescan.png"
INFO_ICON = "info.png"
PLAY_ICON = "play.png"
PAUSE_ICON = "pause.png"
STOP_ICON = "stop.png"
# Named for where they sit rather than for what they do, as the artwork is.
# The glyphs are the usual bar and triangle, so they mean previous and next.
PREVIOUS_ICON = "jump-left.png"
NEXT_ICON = "jump-right.png"
VOLUME_ICON = "volume.png"
SHUFFLE_ICON = "shuffle.png"
VIEW_ICON = "view.png"
MEDIUM_GRID_ICON = "medium-grid.png"
LARGE_GRID_ICON = "large-grid.png"
EXTRA_LARGE_GRID_ICON = "extra-large-grid.png"
DONATE_ICON = "donate.png"
LIBRARY_HEALTH_ICON = "library-health.png"
SEARCH_ICON = "search.png"
REPEAT_ICON = "repeat.png"
REPEAT_ALBUM_ICON = "repeat-album.png"
REPEAT_ONE_ICON = "repeat-1-track.png"
UNMUTE_ICON = "unmute.png"
# The cross laid over one of the three switches above to say it is off. It is
# artwork in its own right rather than a variant of each icon, so a change to
# the cross reaches all three without three files being redrawn.
NEGATIVE_ICON = "negative.png"


def _roots() -> tuple[pathlib.Path, ...]:
    """Every directory an asset could reasonably be found under."""
    here = pathlib.Path(__file__).resolve()
    candidates = [here.parents[2], here.parents[1], here.parent]
    bundled = getattr(sys, "_MEIPASS", None)
    if bundled:
        candidates.append(pathlib.Path(bundled))
    candidates.append(pathlib.Path(sys.argv[0]).resolve().parent)
    return tuple(candidates)


def find_asset(name: str) -> pathlib.Path | None:
    """The bundled asset with this name; None when it cannot be located."""
    for root in _roots():
        for candidate in (root / ASSETS_DIR / name, root / name):
            if candidate.is_file():
                return candidate
    return None


def window_icon_path() -> pathlib.Path | None:
    """The PNG used for the window, the tray and the About badge."""
    return find_asset(WINDOW_ICON)


def application_icon_path() -> pathlib.Path | None:
    """The multi-size icon used for shortcuts and the taskbar."""
    return find_asset(APPLICATION_ICON)


def light_mode_icon_path() -> pathlib.Path | None:
    """The artwork for switching to the light appearance."""
    return find_asset(LIGHT_MODE_ICON)


def dark_mode_icon_path() -> pathlib.Path | None:
    """The artwork for switching to the dark appearance."""
    return find_asset(DARK_MODE_ICON)


def choose_folder_icon_path() -> pathlib.Path | None:
    """The artwork for choosing the music folder."""
    return find_asset(CHOOSE_FOLDER_ICON)


def search_icon_path() -> pathlib.Path | None:
    """The magnifier on the button that opens the search box."""
    return find_asset(SEARCH_ICON)


def rescan_icon_path() -> pathlib.Path | None:
    """The artwork for rescanning the library."""
    return find_asset(RESCAN_ICON)


def info_icon_path() -> pathlib.Path | None:
    """The artwork for the About dialog."""
    return find_asset(INFO_ICON)


def play_icon_path() -> pathlib.Path | None:
    """The artwork for starting or resuming playback."""
    return find_asset(PLAY_ICON)


def pause_icon_path() -> pathlib.Path | None:
    """The artwork the play button wears while something is playing."""
    return find_asset(PAUSE_ICON)


def stop_icon_path() -> pathlib.Path | None:
    """The artwork for ending playback."""
    return find_asset(STOP_ICON)


def previous_icon_path() -> pathlib.Path | None:
    """The artwork for the track before this one."""
    return find_asset(PREVIOUS_ICON)


def next_icon_path() -> pathlib.Path | None:
    """The artwork for the track after this one."""
    return find_asset(NEXT_ICON)


def volume_icon_path() -> pathlib.Path | None:
    """The artwork for the volume control."""
    return find_asset(VOLUME_ICON)


def shuffle_icon_path() -> pathlib.Path | None:
    """The artwork for playing an album out of order."""
    return find_asset(SHUFFLE_ICON)


def view_icon_path() -> pathlib.Path | None:
    """The artwork for switching between the list and album art."""
    return find_asset(VIEW_ICON)


def medium_grid_icon_path() -> pathlib.Path | None:
    """The artwork for moving the grid to medium sleeves."""
    return find_asset(MEDIUM_GRID_ICON)


def large_grid_icon_path() -> pathlib.Path | None:
    """The artwork for moving the grid to large sleeves."""
    return find_asset(LARGE_GRID_ICON)


def extra_large_grid_icon_path() -> pathlib.Path | None:
    """The artwork for moving the grid to extra large sleeves."""
    return find_asset(EXTRA_LARGE_GRID_ICON)


def donate_icon_path() -> pathlib.Path | None:
    """The artwork for the button that offers to buy the author a drink."""
    return find_asset(DONATE_ICON)


def library_health_icon_path() -> pathlib.Path | None:
    """The artwork for repairing what the library health report lists."""
    return find_asset(LIBRARY_HEALTH_ICON)


def repeat_icon_path() -> pathlib.Path | None:
    """The artwork for the repeat switch while it is off."""
    return find_asset(REPEAT_ICON)


def repeat_album_icon_path() -> pathlib.Path | None:
    """The artwork for starting the album again at its end."""
    return find_asset(REPEAT_ALBUM_ICON)


def repeat_one_icon_path() -> pathlib.Path | None:
    """The artwork for holding one track, which carries its own numeral."""
    return find_asset(REPEAT_ONE_ICON)


def unmute_icon_path() -> pathlib.Path | None:
    """The artwork for the mute switch, struck through while silent."""
    return find_asset(UNMUTE_ICON)


def negative_icon_path() -> pathlib.Path | None:
    """The cross that says a switch is off."""
    return find_asset(NEGATIVE_ICON)


def model_licence_path() -> pathlib.Path | None:
    """The GPL-3.0 text covering everything but the interface."""
    return find_asset(MODEL_LICENCE)


def ui_licence_path() -> pathlib.Path | None:
    """The LGPL-3.0 text covering the Qt layer."""
    return find_asset(UI_LICENCE)
