"""What an install is going to do, as one value passed between the layers."""

from __future__ import annotations

import pathlib
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class InstallPlan:
    """Where an install will go and what it will register."""

    target: pathlib.Path
    version: str
    desktop_shortcut: bool = True
    start_menu_shortcut: bool = True
    start_on_sign_in: bool = False
    start_minimised: bool = False
