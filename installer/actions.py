"""What installing and uninstalling actually do.

Everything is per user, so Windows never asks for administrator rights: files
under %LOCALAPPDATA%\\Programs, the uninstall record under HKCU. The UI is a
thin shell over this module and owns no install logic of its own.
"""

from __future__ import annotations

import itertools
import os
import pathlib
import shutil
import subprocess
import sys
import zipfile
from collections.abc import Callable

from installer.plan import InstallPlan
from installer.registry import (
    clear_sign_in_entry,
    register,
    set_sign_in_entry,
    unregister,
)
from stellody.infrastructure import switch_reset
from stellody.infrastructure.paths import data_location
from stellody.shared.version import APP_NAME

EXE_NAME = f"{APP_NAME}.exe"
PAYLOAD_ZIP = "payload.zip"
PAYLOAD_DIR = "payload"
STAGE_DIR = "stage"
ONEFILE_ENV = "NUITKA_ONEFILE_BINARY"
UNINSTALL_DIR = "_uninstall"
SETUP_NAME = f"{APP_NAME}Setup.exe"
UNINSTALL_FLAG = "--uninstall"


# What the setup program reports as it works. The steps are named rather than
# timed, because the only honest thing a bar can show here is which step is
# running: the payload is one large file, so a byte count would sit still and
# then jump.
ProgressCallback = Callable[[int, str], None]
# Measured 2026-08-28: the whole install is 1.08s, of which each shortcut takes
# 0.53s and everything else together takes 0.05s. So the ladder is weighted by
# where the TIME goes rather than by the number of steps; weighting it by steps
# sent the bar to 95% within a twentieth of a second and left it sitting there
# for the rest of the install, which reads as a bar that never worked.
PCT_START = 2
PCT_EXTRACTED = 5
PCT_UNINSTALLER = 8
PCT_REGISTRY = 10
PCT_DESKTOP = 50
PCT_START_MENU = 90
PCT_SIGN_IN = 95
PCT_DONE = 100

# Windows only; absent elsewhere, so it is read rather than named.
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def silent(percent: int, message: str) -> None:
    """The default progress sink, for callers that show nothing."""


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


def version_key(version: str) -> tuple[int, ...]:
    """A dotted version as comparable numbers, ignoring any trailing label."""
    parts = []
    for chunk in version.split("."):
        digits = "".join(itertools.takewhile(str.isdigit, chunk))
        parts.append(int(digits) if digits else 0)
    return tuple(parts)


def payload_roots() -> tuple[pathlib.Path, ...]:
    """Every directory the bundled payload could reasonably sit under.

    Measured under a Nuitka onefile build: `sys.argv[0]` is the ORIGINAL
    executable the user launched, while `__file__` sits in the temporary
    directory the bundle was unpacked into, with the bundled data beside it.
    Resolving the bundle from `sys.argv[0]` therefore searches the folder the
    setup file was downloaded to and finds nothing, which is exactly what made
    setup report a missing payload. `NUITKA_ONEFILE_BINARY` is not set by this
    Nuitka version, so it cannot stand in either.

    The roots are searched rather than deduced, because the same module runs
    from a source checkout, from the unpack directory and as a package
    submodule one level below it.
    """
    here = pathlib.Path(__file__).resolve()
    roots = [here.parents[1], here.parent, here.parent / STAGE_DIR]
    main_file = getattr(sys.modules.get("__main__"), "__file__", None)
    if main_file:
        roots.insert(0, pathlib.Path(main_file).resolve().parent)
    roots.append(pathlib.Path(sys.argv[0]).resolve().parent)
    return tuple(dict.fromkeys(roots))


def payload_zip() -> pathlib.Path | None:
    """The embedded application archive; None when it cannot be found."""
    for root in payload_roots():
        for candidate in (root / PAYLOAD_DIR / PAYLOAD_ZIP, root / PAYLOAD_ZIP):
            if candidate.is_file():
                return candidate
    return None


def setup_executable() -> pathlib.Path:
    """This setup program's own path, as the user launched it.

    Measured under a Nuitka onefile build: `sys.argv[0]` already IS the file the
    user double-clicked, so it is the answer rather than a fallback. The
    environment variable is consulted first only because a future Nuitka may set
    it; this version does not, which is why it must never be relied on alone.
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


def _run_powershell(script: str) -> bool:
    """Run one PowerShell statement, reporting whether it succeeded.

    The setup program is built with no console of its own, so a console child
    process is given a BRAND NEW WINDOW by Windows: a black box that flashes up
    over the installer for as long as PowerShell takes to start. NO_WINDOW stops
    that, which also stops it covering the progress the user is trying to watch.
    """
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
        creationflags=NO_WINDOW,
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


def shortcut_paths() -> tuple[pathlib.Path, ...]:
    """Every shortcut an install may have created."""
    return (
        desktop_dir() / f"{APP_NAME}.lnk",
        start_menu_dir() / f"{APP_NAME}.lnk",
    )


def forget_switches() -> None:
    """Ask the application to start with shuffle and repeat off.

    A note in Stellody's own directory rather than a write into its database.
    The setup program runs at the one moment that database is least safe to
    touch: it has just ended the application by force. Writing to it there
    hung an install once and left the application unable to start after
    another, so the application, which owns the database, does the writing.
    """
    switch_reset.leave(data_location())


def install(
    plan: InstallPlan,
    archive: pathlib.Path,
    progress: ProgressCallback = silent,
    anew: bool = False,
) -> pathlib.Path:
    """Deploy the application, register it and place its shortcuts.

    Installing anew, which is a first install or a reinstall, starts the
    switches off. An update and a downgrade are the same install carrying on,
    so they leave everything the user chose exactly where it was.
    """
    if anew:
        progress(PCT_START, "Clearing the remembered switches...")
        forget_switches()
    progress(PCT_START, "Preparing the install folder...")
    if plan.target.exists():
        shutil.rmtree(plan.target, ignore_errors=True)
    progress(PCT_START, "Extracting files...")
    extract_payload(archive, plan.target)
    progress(PCT_EXTRACTED, "Files extracted.")
    executable = plan.target / EXE_NAME
    # The icon is read out of the executable itself, which carries it in its
    # PE resources. A onefile build ships no loose asset files to point at.
    icon = executable
    uninstaller = plan.target / UNINSTALL_DIR / SETUP_NAME
    uninstaller.parent.mkdir(parents=True, exist_ok=True)
    progress(PCT_UNINSTALLER, "Registering the uninstaller...")
    shutil.copy2(setup_executable(), uninstaller)
    progress(PCT_REGISTRY, "Writing the Apps list entry...")
    register(plan, uninstaller)
    # Each shortcut is reported on its own, because each one is half of the
    # install's whole running time.
    if plan.desktop_shortcut:
        progress(PCT_REGISTRY, "Creating the desktop shortcut...")
        create_shortcut(desktop_dir() / f"{APP_NAME}.lnk", executable, icon)
    progress(PCT_DESKTOP, "Creating the Start Menu entry...")
    if plan.start_menu_shortcut:
        create_shortcut(start_menu_dir() / f"{APP_NAME}.lnk", executable, icon)
    progress(PCT_START_MENU, "Recording how it starts...")
    set_sign_in_entry(executable, plan)
    progress(PCT_SIGN_IN, "Finishing...")
    progress(PCT_DONE, "Done.")
    return executable


def repair(
    target: pathlib.Path,
    archive: pathlib.Path,
    progress: ProgressCallback = silent,
) -> pathlib.Path:
    """Write the application files back over the install, changing nothing else.

    The shortcuts, the Apps list entry and the sign-in choice are all left
    exactly as they are: that is the whole of the difference between a repair
    and a reinstall; it is also why a repair asks no questions.
    """
    progress(PCT_START, "Checking the install folder...")
    progress(PCT_START, "Writing the files back...")
    extract_payload(archive, target)
    progress(PCT_DONE, "Done.")
    return target / EXE_NAME


def set_shortcuts(executable: pathlib.Path, desktop: bool, start_menu: bool) -> None:
    """Put the two shortcuts where the boxes now say they should be."""
    wanted = (desktop, start_menu)
    for link, keep in zip(shortcut_paths(), wanted):
        if keep:
            create_shortcut(link, executable, executable)
        else:
            link.unlink(missing_ok=True)


def uninstall(
    target: pathlib.Path,
    progress: ProgressCallback = silent,
    remove_data: bool = False,
) -> None:
    """Remove the application, its shortcuts and its Apps list entry.

    Stellody's own directory is left alone unless the user asked for it to go.
    It holds the library index, the ratings and play counts, the tags stated by
    hand, the corrections accepted plus the settings: all of it work somebody
    did rather than anything a reinstall could rebuild, so keeping it is the
    default.
    """
    progress(PCT_START, "Removing shortcuts...")
    for link in shortcut_paths():
        link.unlink(missing_ok=True)
    clear_sign_in_entry()
    progress(PCT_DESKTOP, "Removing the Apps list entry...")
    unregister()
    progress(PCT_START_MENU, "Removing files...")
    shutil.rmtree(target, ignore_errors=True)
    if remove_data:
        progress(PCT_SIGN_IN, "Removing the library index...")
        shutil.rmtree(data_location(), ignore_errors=True)
    progress(PCT_DONE, "Done.")
