"""What the backup commands are called, for the menu and the guide alike.

Its own module so the guide can read the labels without importing the menus,
which import the guide. One home, so the guide can never name a command the
menu does not show. BACKUP.md FR-B01, FR-B19.
"""

from __future__ import annotations

from stellody.ui.lift_menu import AMPERSAND

BACK_UP_LABEL = "&Back up library..."
RESTORE_LABEL = "Res&tore from backup..."
ELLIPSIS = "..."


def spoken(label: str) -> str:
    """A menu label as a sentence names it: no access key, no ellipsis."""
    return label.replace(AMPERSAND, "").removesuffix(ELLIPSIS)
