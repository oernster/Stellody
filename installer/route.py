"""Which conversation the setup program is having.

One reading of the machine decides everything the window then shows: the
screen, its heading, the options on it and the buttons under it. Deciding it
once, here, is what stops the four screens drifting apart, which is how a
downgrade came to be announced under a heading saying the newer version was
already installed.

Pure, so every state can be asserted in a test rather than read off a
screenshot.
"""

from __future__ import annotations

import enum

from installer.actions import version_key


class Route(enum.Enum):
    """The five states setup can be run in."""

    INSTALL = "install"
    UPDATE = "update"
    DOWNGRADE = "downgrade"
    MANAGE = "manage"
    UNINSTALL = "uninstall"


def route_for(installed: str, version: str, uninstalling: bool) -> Route:
    """Which route this run takes, from what is recorded as installed.

    Being asked to uninstall settles it before anything else is considered,
    because that is the one route the user names rather than setup deducing.
    """
    if uninstalling:
        return Route.UNINSTALL
    if not installed:
        return Route.INSTALL
    here, arriving = version_key(installed), version_key(version)
    if here < arriving:
        return Route.UPDATE
    if here > arriving:
        return Route.DOWNGRADE
    return Route.MANAGE
