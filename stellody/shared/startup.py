"""How Stellody is asked to start.

The setup program writes the sign-in entry that launches Stellody, so the flag
meaning "start in the tray" has to mean the same thing on both sides of that
handover. It lives here so there is exactly one place that spells it.
"""

from __future__ import annotations

from collections.abc import Iterable

HIDDEN_FLAG = "--hidden"


def starts_hidden(arguments: Iterable[str]) -> bool:
    """True when the command line asked Stellody to start in the tray."""
    return HIDDEN_FLAG in tuple(arguments)
