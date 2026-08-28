"""Everything the setup program writes into the registry.

All of it is per user under HKCU, so Windows never asks for administrator
rights: the Apps list entry that offers to remove Stellody, plus the
sign-in entry that starts it. Both are written here so there is one place that knows
what setup leaves behind; one place that takes it away again.
"""

from __future__ import annotations

import pathlib

from installer.plan import InstallPlan
from stellody.shared.startup import HIDDEN_FLAG

APP_NAME = "Stellody"
EXE_NAME = f"{APP_NAME}.exe"
UNINSTALL_FLAG = "--uninstall"
REGISTRY_ROOT = r"Software\Microsoft\Windows\CurrentVersion\Uninstall"
RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
PUBLISHER = "Oliver Ernster"
BYTES_PER_KIB = 1024


def installed_size_kib(target: pathlib.Path) -> int:
    """How much space the install takes, as Windows records it."""
    total = sum(item.stat().st_size for item in target.rglob("*") if item.is_file())
    return total // BYTES_PER_KIB


def registry_key() -> str:
    """The uninstall key Stellody registers itself under."""
    return f"{REGISTRY_ROOT}\\{APP_NAME}"


def register(plan: InstallPlan, uninstaller: pathlib.Path) -> None:
    """Write the Apps list entry so Windows can offer to remove Stellody."""
    import winreg

    executable = plan.target / EXE_NAME
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, registry_key()) as key:
        values = {
            "DisplayName": APP_NAME,
            "DisplayVersion": plan.version,
            "InstallLocation": str(plan.target),
            "UninstallString": f'"{uninstaller}" {UNINSTALL_FLAG}',
            "DisplayIcon": str(executable),
            "Publisher": PUBLISHER,
        }
        for name, value in values.items():
            winreg.SetValueEx(key, name, 0, winreg.REG_SZ, value)
        for name in ("NoModify", "NoRepair"):
            winreg.SetValueEx(key, name, 0, winreg.REG_DWORD, 1)
        winreg.SetValueEx(
            key, "EstimatedSize", 0, winreg.REG_DWORD, installed_size_kib(plan.target)
        )


def sign_in_command(executable: pathlib.Path) -> str:
    """The value the sign-in entry holds: a quoted path, plus the tray flag.

    A sign-in start is ALWAYS a quiet one. Asking a second question about it
    offered a choice nobody wants the other half of: an application appearing
    over whatever Windows has just finished putting on screen.
    """
    return f'"{executable}" {HIDDEN_FLAG}'


def write_sign_in_entry(executable: pathlib.Path, wanted: bool) -> None:
    """Write or clear the per-user Run entry, so the two never disagree.

    One entry is written whichever way the choice went, because leaving a
    stale entry behind is how an unticked box still launches something.
    """
    import winreg

    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
        if not wanted:
            try:
                winreg.DeleteValue(key, APP_NAME)
            except OSError:
                pass
            return
        command = sign_in_command(executable)
        winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, command)


def set_sign_in_entry(executable: pathlib.Path, plan: InstallPlan) -> None:
    """Record how an install asked to start."""
    write_sign_in_entry(executable, plan.start_on_sign_in)


def read_sign_in_command() -> str:
    """The command the Run entry currently holds; empty when there is none."""
    import winreg

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
            return str(winreg.QueryValueEx(key, APP_NAME)[0])
    except OSError:
        return ""


def clear_sign_in_entry() -> None:
    """Remove the sign-in entry, so an uninstall leaves nothing launching."""
    import winreg

    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE
        ) as key:
            winreg.DeleteValue(key, APP_NAME)
    except OSError:
        pass


def read_registered() -> dict[str, str]:
    """What the Apps list currently records, empty when nothing is installed."""
    import winreg

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, registry_key()) as key:
            found: dict[str, str] = {}
            for name in ("DisplayVersion", "InstallLocation"):
                try:
                    found[name] = str(winreg.QueryValueEx(key, name)[0])
                except OSError:
                    continue
            return found
    except OSError:
        return {}


def unregister() -> None:
    """Remove the Apps list entry."""
    import winreg

    try:
        winreg.DeleteKey(winreg.HKEY_CURRENT_USER, registry_key())
    except OSError:
        pass
