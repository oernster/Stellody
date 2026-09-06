"""How a path is written on screen.

Qt's folder dialog hands back forward slashes on every platform, while the walk
joins its folders with the separator the operating system actually uses. Shown
side by side on one status line that reads as two different machines:

    Scanning H:/FLACMusic
    <percent>% (<done> of <total>) H:/FLACMusic\\Massive Attack\\Mezzanine

Stellody stores what it was given and writes the native form when it shows it,
so nothing stored has to change for the window to read properly.
"""

from __future__ import annotations

import os


def native_path(path: str) -> str:
    """One path, written the way this operating system writes one.

    An empty path stays empty: normpath would answer the current directory;
    "nothing chosen yet" is not a folder called dot.
    """
    if not path:
        return path
    return os.path.normpath(path)
