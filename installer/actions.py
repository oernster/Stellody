"""What installing and uninstalling actually do.

Everything is per user, so Windows never asks for administrator rights: files
under %LOCALAPPDATA%\\Programs, the uninstall record under HKCU. The UI is a
thin shell over this module and owns no install logic of its own.
"""

from __future__ import annotations

import os
import pathlib
import shutil
import subprocess
import sys
import zipfile
from dataclasses import dataclass

APP_NAME = "Stellody"
EXE_NAME = f"{APP_NAME}.exe"
PAYLOAD_ZIP = "payload.zip"
PAYLOAD_DIR = "payload"
ONEFILE_ENV = "NUITKA_ONEFILE_BINARY"
UNINSTALL_DIR = "_uninstall"
SETUP_NAME = f"{APP_NAME}Setup.exe"
UNINSTALL_FLAG = "--uninstall"

REGISTRY_ROOT = r"Software\Microsoft\Windows\CurrentVersion\Uninstall"
PUBLISHER = "Oliver Ernster"
BYTES_PER_KIB = 1024


@dataclass(frozen=True, slots=True)
class InstallPlan:
    """Where an install will go and what it will register."""

    target: pathlib.Path
    version: str
    desktop_shortcut: bool = True
    start_menu_shortcut: bool = True


def programs_dir() -> pathlib.Path:
    """The per-user Programs directory Windows expects an app to live in."""
    local = os.environ.get("LOCALAPPDATA")
    base = pathlib.Path(local) if local else pathlib.Path.home() / "AppData" / "Local"
    return base / "Programs"


def default_target() -> pathlib.Path:
    """Where Stellody installs unless told otherwise."""
    return programs_dir() / APP_NAME


def desktop_dir() -> pathlib.Path:
    """The current user's Desktop."""
    return pathlib.Path(os.path.expanduser("~")) / "Desktop"


def start_menu_dir() -> pathlib.Path:
    """The current user's Start Menu programs folder."""
    appdata = os.environ.get("APPDATA")
    base = pathlib.Path(appdata) if appdata else pathlib.Path.home() / "AppData/Roaming"
    return base / "Microsoft" / "Windows" / "Start Menu" / "Programs"


def bundle_root() -> pathlib.Path:
    """Where this setup program's own bundled files were unpacked."""
    frozen = getattr(sys, "frozen", False) or "__compiled__" in globals()
    if frozen or not __file__.endswith(".py"):
        return pathlib.Path(sys.argv[0]).resolve().parent
    return pathlib.Path(__file__).resolve().parents[1]


def payload_zip() -> pathlib.Path | None:
    """The embedded application archive; None when it cannot be found."""
    for candidate in (
        bundle_root() / PAYLOAD_DIR / PAYLOAD_ZIP,
        bundle_root() / PAYLOAD_ZIP,
    ):
        if candidate.is_file():
            return candidate
    return None


def setup_executable() -> pathlib.Path:
    """This setup program's own path, as the user launched it.

    Under a Nuitka onefile build sys.argv[0] points at the unpacked temporary
    bootstrap rather than the file the user double-clicked, so the real path
    comes from the environment variable Nuitka sets for exactly this reason.
    """
    original = os.environ.get(ONEFILE_ENV)
    if original:
        return pathlib.Path(original).resolve()
    return pathlib.Path(sys.argv[0]).resolve()


def _is_inside(base: pathlib.Path, candidate: pathlib.Path) -> bool:
    """True when a path stays within a directory once resolved."""
    try:
        candidate.resolve().relative_to(base.resolve())
    except ValueError:
        return False
    return True


def extract_payload(archive: pathlib.Path, target: pathlib.Path) -> int:
    """Unpack the application into its install directory.

    Every entry is checked against the target first, so a crafted archive
    cannot write outside the directory the user chose.
    """
    target.mkdir(parents=True, exist_ok=True)
    written = 0
    with zipfile.ZipFile(archive) as bundle:
        for entry in bundle.namelist():
            destination = target / entry
            if not _is_inside(target, destination):
                raise ValueError(f"archive entry escapes the install folder: {entry}")
        for entry in bundle.namelist():
            bundle.extract(entry, target)
            written += 1
    return written


def installed_size_kib(target: pathlib.Path) -> int:
    """How much space the install takes, as Windows records it."""
    total = sum(item.stat().st_size for item in target.rglob("*") if item.is_file())
    return total // BYTES_PER_KIB


def _run_powershell(script: str) -> bool:
    """Run one PowerShell statement, reporting whether it succeeded."""
    result = subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-NonInteractive",
            "-ExecutionPolicy",
            "Bypass",
            "-Command",
            script,
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode == 0


def create_shortcut(
    link: pathlib.Path, executable: pathlib.Path, icon: pathlib.Path | None
) -> bool:
    """Create a Windows shortcut pointing at the installed application."""
    link.parent.mkdir(parents=True, exist_ok=True)
    icon_line = (
        f"$s.IconLocation = '{icon}';" if icon is not None and icon.exists() else ""
    )
    script = (
        "$w = New-Object -ComObject WScript.Shell;"
        f"$s = $w.CreateShortcut('{link}');"
        f"$s.TargetPath = '{executable}';"
        f"$s.WorkingDirectory = '{executable.parent}';"
        f"$s.Description = '{APP_NAME}';"
        f"{icon_line}"
        "$s.Save()"
    )
    return _run_powershell(script)


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


def shortcut_paths() -> tuple[pathlib.Path, ...]:
    """Every shortcut an install may have created."""
    return (
        desktop_dir() / f"{APP_NAME}.lnk",
        start_menu_dir() / f"{APP_NAME}.lnk",
    )


def install(plan: InstallPlan, archive: pathlib.Path) -> pathlib.Path:
    """Deploy the application, register it and place its shortcuts."""
    if plan.target.exists():
        shutil.rmtree(plan.target, ignore_errors=True)
    extract_payload(archive, plan.target)
    executable = plan.target / EXE_NAME
    # The icon is read out of the executable itself, which carries it in its
    # PE resources. A onefile build ships no loose asset files to point at.
    icon = executable
    uninstaller = plan.target / UNINSTALL_DIR / SETUP_NAME
    uninstaller.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(setup_executable(), uninstaller)
    register(plan, uninstaller)
    if plan.desktop_shortcut:
        create_shortcut(desktop_dir() / f"{APP_NAME}.lnk", executable, icon)
    if plan.start_menu_shortcut:
        create_shortcut(start_menu_dir() / f"{APP_NAME}.lnk", executable, icon)
    return executable


def uninstall(target: pathlib.Path) -> None:
    """Remove the application, its shortcuts and its Apps list entry.

    Stellody's own database is left alone: it holds the user's library view,
    which they may want back if they reinstall.
    """
    for link in shortcut_paths():
        link.unlink(missing_ok=True)
    unregister()
    shutil.rmtree(target, ignore_errors=True)
