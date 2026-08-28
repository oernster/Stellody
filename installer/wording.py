"""What the setup program says, decided from the route it is on.

Pure text decisions with no Qt in sight, so the wording for every install state
can be asserted in a test rather than read off a screenshot. The route is
decided once and handed here; nothing in this module re-derives it.
"""

from __future__ import annotations

from installer.actions import APP_NAME
from installer.route import Route

PRIMARY_LABELS = {
    Route.INSTALL: "Install",
    Route.UPDATE: "Update",
    Route.DOWNGRADE: "Go back",
    Route.MANAGE: "Repair",
    Route.UNINSTALL: "Uninstall",
}

LEADS = {
    Route.INSTALL: (
        "This installs for your account only, so Windows will not ask for "
        "administrator rights."
    ),
    Route.UPDATE: (
        "A newer version is ready to install. Your music and your library are "
        "untouched."
    ),
    Route.DOWNGRADE: (
        "This setup file carries an older version than the one installed. Your "
        "music and your library are untouched."
    ),
    Route.MANAGE: (
        "Repair puts the files back and leaves everything else alone. "
        "Reinstall writes them again with the choices below."
    ),
    Route.UNINSTALL: (
        f"This removes {APP_NAME} and its shortcuts. Your music is never " "touched."
    ),
}


def primary_label(route: Route) -> str:
    """What the go-ahead button on this route does."""
    return PRIMARY_LABELS[route]


def heading(route: Route, installed: str, version: str) -> str:
    """The screen heading, which is where a single version belongs.

    An update and a downgrade name no version here: they are about two of
    them, so both are shown in the flow line under the heading instead.
    """
    if route is Route.UNINSTALL:
        return f"Remove {APP_NAME} {installed or version}?"
    if route is Route.INSTALL:
        return f"Install {APP_NAME} {version}"
    if route is Route.UPDATE:
        return "Update available"
    if route is Route.DOWNGRADE:
        return "Go back a version?"
    return f"{APP_NAME} {installed} is installed"


def lead(route: Route) -> str:
    """The muted line under the heading."""
    return LEADS[route]


LAUNCH_LABEL = f"Start {APP_NAME} and close setup when this finishes"
DESKTOP_LABEL = "Add a Desktop shortcut"
START_MENU_LABEL = "Add a Start Menu entry"
START_MENU_HINT = "Find it by typing its name in the Start Menu."
SIGN_IN_LABEL = f"Start {APP_NAME} when I sign in"
SIGN_IN_HINT = f"{APP_NAME} opens with Windows instead of waiting to be asked."
MINIMISED_LABEL = "Start minimised to the notification area"
MINIMISED_HINT = "It waits quietly in the notification area until you open it."

# The library index and the window's settings share one database, so removing
# either removes both. The box says so rather than naming the smaller of them
# and quietly taking the other.
FORGET_LABEL = "Also remove my library index and settings"
FORGET_HINT = (
    "That is the scan of your music and what the window remembers, not the "
    "music itself. It cannot be undone."
)

RUNNING_HEADING = f"{APP_NAME} is open"
RUNNING_LEAD = (
    "It has to close before setup can replace its files. Closing it affects "
    f"nothing beyond stopping playback until you start {APP_NAME} again."
)
STILL_RUNNING_LEAD = (
    "Setup could not close it. Close it yourself, then run setup again."
)
LAUNCHING_LEAD = "It is starting now."
KEPT_LIBRARY_LEAD = (
    "Your music was never touched; the library index has been left in place."
)
REMOVED_LIBRARY_LEAD = (
    "Your music was never touched; the library index and settings are gone."
)
REPAIRED_LEAD = "The files have been put back and nothing else was changed."
REINSTALLED_LEAD = (
    "The files were written again and the shortcuts put back as a new install "
    "would leave them."
)
