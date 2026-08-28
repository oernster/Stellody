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


def rescan_icon_path() -> pathlib.Path | None:
    """The artwork for rescanning the library."""
    return find_asset(RESCAN_ICON)


def info_icon_path() -> pathlib.Path | None:
    """The artwork for the About dialog."""
    return find_asset(INFO_ICON)


def model_licence_path() -> pathlib.Path | None:
    """The GPL-3.0 text covering everything but the interface."""
    return find_asset(MODEL_LICENCE)


def ui_licence_path() -> pathlib.Path | None:
    """The LGPL-3.0 text covering the Qt layer."""
    return find_asset(UI_LICENCE)
