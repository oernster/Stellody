"""Generate every platform icon asset from the single master artwork.

The master is assets/application-icon.png. Everything else in assets/ that is
an icon is produced by this script, so there is one source of truth for the
artwork and no hand-edited derivative can drift from it.

Run:  python generate_icons.py
"""

from __future__ import annotations

import pathlib
import sys

from PIL import Image

ASSETS = pathlib.Path(__file__).resolve().parent / "assets"
MASTER = ASSETS / "application-icon.png"

APP_SLUG = "stellody"
PNG_SIZES = (16, 24, 32, 48, 64, 96, 128, 256, 512, 1024)
ICO_SIZES = (16, 24, 32, 48, 64, 128, 256)
CANONICAL_SIZE = 256
ICNS_SIZE = 1024

RESAMPLE = Image.Resampling.LANCZOS


def load_master() -> Image.Image:
    """Open the master artwork, insisting it is square and has an alpha channel."""
    if not MASTER.exists():
        raise SystemExit(f"master artwork not found: {MASTER}")
    master = Image.open(MASTER).convert("RGBA")
    if master.width != master.height:
        raise SystemExit(
            f"master artwork must be square, found {master.width}x{master.height}"
        )
    if master.width < max(PNG_SIZES):
        raise SystemExit(
            f"master artwork is {master.width}px; icons are never upscaled, so it "
            f"must be at least {max(PNG_SIZES)}px"
        )
    return master


def scaled(master: Image.Image, size: int) -> Image.Image:
    """The master reduced to one size. Reduction only, never enlargement."""
    return master.resize((size, size), RESAMPLE)


def write_pngs(master: Image.Image) -> list[pathlib.Path]:
    """One PNG per size, plus the canonical unsuffixed name."""
    written: list[pathlib.Path] = []
    for size in PNG_SIZES:
        target = ASSETS / f"{APP_SLUG}_icon_{size}.png"
        scaled(master, size).save(target, format="PNG")
        written.append(target)
    canonical = ASSETS / f"{APP_SLUG}_icon.png"
    scaled(master, CANONICAL_SIZE).save(canonical, format="PNG")
    written.append(canonical)
    return written


def write_ico(master: Image.Image) -> pathlib.Path:
    """The multi-size Windows icon used by the exe, installer and shortcuts."""
    target = ASSETS / f"{APP_SLUG}.ico"
    scaled(master, max(ICO_SIZES)).save(
        target, format="ICO", sizes=[(size, size) for size in ICO_SIZES]
    )
    return target


def write_icns(master: Image.Image) -> pathlib.Path | None:
    """The macOS bundle icon, where the running platform can produce one."""
    target = ASSETS / f"{APP_SLUG}.icns"
    try:
        scaled(master, ICNS_SIZE).save(target, format="ICNS")
    except (OSError, ValueError) as error:
        print(f"  skipped {target.name}: {error}")
        return None
    return target


def main() -> int:
    """Regenerate the whole icon set."""
    master = load_master()
    print(f"master: {MASTER.name} ({master.width}x{master.height})")
    produced: list[pathlib.Path] = []
    produced.extend(write_pngs(master))
    produced.append(write_ico(master))
    icns = write_icns(master)
    if icns is not None:
        produced.append(icns)
    for path in produced:
        print(f"  wrote {path.name}")
    print(f"{len(produced)} asset(s) written to {ASSETS}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
