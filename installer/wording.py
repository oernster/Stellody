"""What the setup program says, decided from what is already installed.

Pure text decisions with no Qt in sight, so the wording for every install state
can be asserted in a test rather than read off a screenshot.
"""

from __future__ import annotations

from installer.actions import APP_NAME, version_key


def primary_label(installed: str, version: str, uninstalling: bool) -> str:
    """What the go-ahead button does, given what is already there."""
    if uninstalling:
        return "Uninstall"
    if not installed:
        return "Install"
    if version_key(installed) < version_key(version):
        return "Update"
    return "Reinstall"


def heading(installed: str, version: str, uninstalling: bool) -> str:
    """The screen heading, which is where the version belongs."""
    if uninstalling:
        return f"Remove {APP_NAME} {installed or version}"
    if not installed:
        return f"Install {APP_NAME} {version}"
    if version_key(installed) < version_key(version):
        return f"Update {installed} to {version}"
    return f"{APP_NAME} {installed} is installed"


def lead(installed: str, version: str, uninstalling: bool) -> str:
    """The muted line under the heading."""
    if uninstalling:
        return (
            f"This removes {APP_NAME} and its shortcuts. Your music is never "
            "touched; the library database is left in place."
        )
    if not installed:
        return (
            "This installs for your account only, so Windows will not ask for "
            "administrator rights."
        )
    if version_key(installed) > version_key(version):
        return (
            "This setup carries an older version than the one installed. "
            "Going ahead replaces it."
        )
    return "Reinstall puts the files back and asks for these choices again."
