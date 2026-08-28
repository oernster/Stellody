"""What is already on this machine, read once before anything is drawn.

Setup used to open every box ticked whatever was actually there, so a user who
had deliberately declined a desktop shortcut was offered one again as though
they had asked for it; a reinstall then silently put it back. The boxes now say
what is true; the reading is taken once and passed around, so no two screens
can disagree about it.
"""

from __future__ import annotations

import pathlib
from dataclasses import dataclass

from installer import actions
from installer.registry import read_registered, read_sign_in_command


@dataclass(frozen=True, slots=True)
class Existing:
    """What the machine already holds, at the moment setup started."""

    version: str
    location: pathlib.Path
    desktop: bool
    start_menu: bool
    sign_in: bool

    @property
    def installed(self) -> bool:
        """Whether there is an install to talk about at all."""
        return bool(self.version)

    @property
    def executable(self) -> pathlib.Path:
        """The installed application, wherever the Apps list says it is."""
        return self.location / actions.EXE_NAME


def look() -> Existing:
    """Read the registry and the shortcut folders as they stand."""
    recorded = read_registered()
    location = pathlib.Path(
        recorded.get("InstallLocation", str(actions.default_target()))
    )
    desktop, start_menu = actions.shortcut_paths()
    command = read_sign_in_command()
    return Existing(
        version=recorded.get("DisplayVersion", ""),
        location=location,
        desktop=desktop.exists(),
        start_menu=start_menu.exists(),
        sign_in=bool(command),
    )
