#!/usr/bin/env python3
"""Embedding a custom volume icon into a finished DMG.

Split out of builddmg.py so each build module stays readable, following the
same division ClearBudget uses.

**It generates no icon.** ClearBudget's version of this file carries a PNG
compositor and an icns generator, because it derives its Mac icon at build
time. Stellody already has one source of truth for every icon it owns:
`generate_icons.py` reads the master artwork and writes `assets/stellody.icns`
alongside the rest of the set. A second generator here would be a second home
for one artefact, which is the thing that lets two answers drift apart, so this
file reads the committed icns and does nothing else with it.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

from build_utils import run, section

# The FinderInfo bit that tells Finder a volume carries its own icon. Written
# by hand only where SetFile is absent, which is the case on a machine with no
# full Xcode installed.
CUSTOM_ICON_FLAG_BYTE = 8
CUSTOM_ICON_FLAG_VALUE = 0x04
FINDER_INFO_LENGTH = 32


def _find_mount_point(hdiutil_stdout: str) -> str | None:
    for line in hdiutil_stdout.splitlines():
        parts = line.split("\t")
        if len(parts) >= 3 and parts[-1].strip().startswith("/Volumes/"):
            return parts[-1].strip()
    return None


def _set_custom_icon_flag(mount_point: str) -> None:
    """Tell Finder to show the volume's own icon rather than the default.

    SetFile lives inside Xcode rather than the command-line tools, so it is
    asked for rather than assumed; where it is absent the same bit is written
    straight into the extended attribute, which is what SetFile does anyway.
    """
    set_file = subprocess.run(
        ["xcrun", "-f", "SetFile"], capture_output=True, text=True, check=False
    ).stdout.strip()
    if set_file:
        subprocess.run([set_file, "-a", "C", mount_point], check=True)
        return
    finder_info = bytearray(FINDER_INFO_LENGTH)
    finder_info[CUSTOM_ICON_FLAG_BYTE] = CUSTOM_ICON_FLAG_VALUE
    subprocess.run(
        [
            "xattr",
            "-wx",
            "com.apple.FinderInfo",
            " ".join(f"{byte:02x}" for byte in finder_info),
            mount_point,
        ],
        check=True,
    )


def set_volume_icon(icns_path: Path, final_dmg: str, rw_dmg_name: str) -> None:
    """Put the application's icon on the disk image's own volume.

    A compressed image cannot be written to, so it is converted to a writable
    one, mounted, given the icon and converted back.
    """
    section("Set volume icon")
    rw_dmg = Path(rw_dmg_name)

    run(["hdiutil", "convert", final_dmg, "-format", "UDRW", "-o", str(rw_dmg)])
    try:
        result = subprocess.run(
            ["hdiutil", "attach", "-noverify", str(rw_dmg)],
            capture_output=True,
            text=True,
            check=True,
        )
        print(f"  $ hdiutil attach -noverify {rw_dmg}")
        mount_point = _find_mount_point(result.stdout)
        if not mount_point:
            sys.exit(
                f"ERROR: could not find mount point in hdiutil output:\n{result.stdout}"
            )

        try:
            shutil.copy(icns_path, Path(mount_point) / ".VolumeIcon.icns")
            _set_custom_icon_flag(mount_point)
            print(f"  Volume icon embedded; custom-icon flag set on {mount_point}")
        finally:
            run(["hdiutil", "detach", mount_point], check=False)

        Path(final_dmg).unlink(missing_ok=True)
        run(["hdiutil", "convert", str(rw_dmg), "-format", "UDZO", "-o", final_dmg])
    finally:
        rw_dmg.unlink(missing_ok=True)
