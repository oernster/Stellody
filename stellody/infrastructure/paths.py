"""Where Stellody keeps its own state.

This is one of the four modules permitted to write to disk; everything it
writes is Stellody's, never the user's music.
"""

from __future__ import annotations

import os
import pathlib
import sys

APP_DIR_NAME = "Stellody"
APP_DIR_SLUG = "stellody"
DATABASE_NAME = "library.sqlite3"
ART_CACHE_DIR = "artwork"


def _windows_base() -> pathlib.Path:
    """The per-user application data directory on Windows."""
    local = os.environ.get("LOCALAPPDATA")
    if local:
        return pathlib.Path(local) / APP_DIR_NAME
    return pathlib.Path.home() / "AppData" / "Local" / APP_DIR_NAME


def _macos_base() -> pathlib.Path:
    """The per-user application support directory on macOS."""
    return pathlib.Path.home() / "Library" / "Application Support" / APP_DIR_NAME


def _xdg_base() -> pathlib.Path:
    """The per-user data directory on Linux and other Unix systems."""
    share = os.environ.get("XDG_DATA_HOME")
    if share:
        return pathlib.Path(share) / APP_DIR_SLUG
    return pathlib.Path.home() / ".local" / "share" / APP_DIR_SLUG


def data_location() -> pathlib.Path:
    """Where Stellody's own directory belongs, whether or not it is there.

    The setup program asks this when it offers to remove that directory;
    an uninstaller that created what it was about to delete would be absurd.
    """
    if sys.platform == "win32":
        return _windows_base()
    if sys.platform == "darwin":
        return _macos_base()
    return _xdg_base()


def data_dir() -> pathlib.Path:
    """Stellody's own directory, created if it is not there yet."""
    base = data_location()
    base.mkdir(parents=True, exist_ok=True)
    return base


def database_path() -> pathlib.Path:
    """The library database file."""
    return data_dir() / DATABASE_NAME


def art_cache_dir() -> pathlib.Path:
    """The directory holding cached cover thumbnails."""
    cache = data_dir() / ART_CACHE_DIR
    cache.mkdir(parents=True, exist_ok=True)
    return cache
