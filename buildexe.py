"""Build the Stellody application with Nuitka.

Onefile by default, which is what ships. Pass --standalone for a directory
bundle instead, which is quicker to inspect when something is wrong.

Run:  python buildexe.py
      python buildexe.py --standalone
"""

from __future__ import annotations

import importlib.metadata
import importlib.util
import itertools
import math
import os
import pathlib
import shutil
import subprocess
import sys
from collections.abc import Iterable

import stamp_sitemap
import stamp_version

# The copyright notice comes from the package rather than being written
# here as well: the exe's file properties and the About box have to say
# the same thing, so they read the same constant.
from stellody.shared.version import COPYRIGHT_NOTICE

ROOT = pathlib.Path(__file__).resolve().parent

APP_DISPLAY_NAME = "Stellody"
APP_AUTHOR = "Oliver Ernster"
EXE_NAME = "Stellody"
ENTRY_SCRIPT = ROOT / "main.py"
ICON_FILE = ROOT / "assets" / "stellody.ico"
VERSION_FILE = ROOT / "VERSION"
DEV_VERSION = "0.0.0-dev"

PAYLOAD_DIR = ROOT / "installer" / "payload"
BUNDLE_DIR = PAYLOAD_DIR / APP_DISPLAY_NAME
NUITKA_DIST_DIR = PAYLOAD_DIR / "main.dist"
ONEFILE_EXE = PAYLOAD_DIR / f"{EXE_NAME}.exe"

ASSETS_DIR = ROOT / "assets"
# Where the assets are copied before being shipped, scaled to fit (see
# `stage_assets`); inside the payload directory, which git ignores.
ASSET_STAGE_DIR = PAYLOAD_DIR / "assets-stage"
ASSET_DESTINATION = "assets"
# Assets only another platform's build reads, never the running application:
# the macOS DMG's icon and file icon, plus the master `generate_icons.py`
# draws every icon from. About 4 MB the Windows bundle carried for nothing.
OTHER_PLATFORM_ASSETS = frozenset(
    {"stellody.icns", "stellody_icon_1024.png", "application-icon.png"}
)
# Windows' display scaling stops at 500%. With the interface scale and the
# largest drawn icon this gives the most pixels any shipped picture can
# fill; the masters are about 1,250 px, almost five times that, which was
# about 65 MB of resolution no screen could show.
WINDOWS_MAX_DISPLAY_SCALE = 5
PICTURE_SUFFIX = ".png"

# Loose files shipped at the bundle root.
DATA_FILES: tuple[pathlib.Path, ...] = (
    VERSION_FILE,
    ROOT / "LICENSE",
    ROOT / "LICENSE-GPL-3.0.txt",
    ROOT / "LICENSE-LGPL-3.0.txt",
)

# Qt plugins and libraries the application never loads, as patterns over the
# bundled paths. Stellody reads JPEG, PNG, WebP and BMP pictures (`walker.py`
# IMAGE_SUFFIXES) and GIF may be embedded, so those stay; PDF (with the 4 MB
# Qt PDF library it drags in), TIFF, ICNS, TGA, WBMP and SVG are never read.
# Windows needs only the `qwindows` platform; the other three are for
# headless runs and Direct2D, which nothing here asks for.
UNUSED_QT_LIBRARIES = (
    "*qt-plugins/imageformats/qpdf*",
    "*qt-plugins/imageformats/qtiff*",
    "*qt-plugins/imageformats/qicns*",
    "*qt-plugins/imageformats/qtga*",
    "*qt-plugins/imageformats/qwbmp*",
    "*qt-plugins/imageformats/qsvg*",
    "*qt-plugins/iconengines/qsvgicon*",
    "*qt-plugins/platforms/qdirect2d*",
    "*qt-plugins/platforms/qoffscreen*",
    "*qt-plugins/platforms/qminimal*",
    "qt6pdf*",
    "qt6svg*",
)
# numpy subpackages nothing reaches: a plain `import numpy` loads none of them
# and neither Stellody nor its audio libraries name them (soundfile's
# `np.random` is in docstring examples). `numpy.fft` stays: `analysing.py`.
UNUSED_MODULES = (
    "numpy.random",
    "numpy.ma",
    "numpy.polynomial",
    "numpy.ctypeslib",
    "numpy.matlib",
    "numpy.testing",
    "numpy.f2py",
)

PE_VERSION_PARTS = 4
CONSOLE_MODE_RELEASE = "disable"
CONSOLE_MODE_DEBUG = "attach"
DEBUG_ENV = "STELLODY_DEBUG"
STANDALONE_FLAG = "--standalone"
BYTES_PER_MIB = 1024 * 1024
# The Nuitka the Windows and macOS builds are written against. One outside
# the range stops the build here, rather than a release nobody chose compiling
# what ships. The ceiling is the first release known to compile a Stellody
# that dies on start (an access violation in main.dll before the window).
NUITKA_MINIMUM = (4, 2, 1)
NUITKA_CEILING = (4, 3)


def require(module: str, package: str) -> None:
    """Stop with a useful message when a build tool is not installed.

    Without this the failure is a bare import error naming a module the reader
    has to map back to a package by themselves.
    """
    if importlib.util.find_spec(module) is None:
        print(
            f"{package} is not installed. It is a build dependency:\n"
            "    python -m pip install -r requirements-dev.txt",
            file=sys.stderr,
        )
        raise SystemExit(1)


def require_nuitka() -> None:
    """Stop where the environment holds a Nuitka outside the range built against."""
    require("nuitka", "Nuitka")
    installed = importlib.metadata.version("nuitka")
    numbers = tuple(
        int("".join(itertools.takewhile(str.isdigit, part)) or 0)
        for part in installed.split(".")
    )
    if NUITKA_MINIMUM <= numbers < NUITKA_CEILING:
        return
    lowest = ".".join(str(number) for number in NUITKA_MINIMUM)
    above = ".".join(str(number) for number in NUITKA_CEILING)
    print(
        f"Nuitka {installed} is installed; this build needs {lowest} or later, "
        f"below {above}:\n"
        "    python -m pip install -r requirements-dev.txt",
        file=sys.stderr,
    )
    raise SystemExit(1)


def read_version() -> str:
    """The one version string, from the one file that holds it."""
    try:
        return VERSION_FILE.read_text(encoding="utf-8").strip() or DEV_VERSION
    except OSError:
        return DEV_VERSION


def pe_version(version: str) -> str:
    """A four part numeric version, which is all Windows PE metadata accepts.

    Anything that is not a digit is dropped from each dotted segment, so a
    version like 0.2.0-rc1 becomes 0.2.0.0.
    """
    parts = [
        "".join(itertools.takewhile(str.isdigit, part)) for part in version.split(".")
    ]
    numbers = [part for part in parts if part][:PE_VERSION_PARTS]
    while len(numbers) < PE_VERSION_PARTS:
        numbers.append("0")
    return ".".join(numbers)


def console_mode() -> str:
    """Show a console only when a debug build is asked for."""
    return CONSOLE_MODE_DEBUG if os.environ.get(DEBUG_ENV) else CONSOLE_MODE_RELEASE


def jobs() -> int:
    """Compile on every core the machine has."""
    return os.cpu_count() or 1


def icon_edge_px() -> int:
    """The most pixels any shipped picture is drawn across, at any scale."""
    from stellody.ui.interface_scale import INTERFACE_SCALE
    from stellody.ui.tray_metrics import ICON_PX

    return math.ceil(ICON_PX * INTERFACE_SCALE * WINDOWS_MAX_DISPLAY_SCALE)


def stage_assets(
    target: pathlib.Path, names: Iterable[str] | None = None
) -> pathlib.Path:
    """Copy the assets to ship into `target`, pictures scaled to fit.

    Every asset but `OTHER_PLATFORM_ASSETS`, else only `names`. A picture
    larger than `icon_edge_px` on its longer side is written at that size,
    keeping its shape; the masters in `assets/` are never touched.
    """
    require("PIL", "Pillow")
    from PIL import Image

    edge = icon_edge_px()
    shutil.rmtree(target, ignore_errors=True)
    target.mkdir(parents=True)
    wanted = None if names is None else set(names)
    for source in sorted(ASSETS_DIR.iterdir()):
        if not source.is_file() or source.name in OTHER_PLATFORM_ASSETS:
            continue
        if wanted is not None and source.name not in wanted:
            continue
        destination = target / source.name
        if source.suffix.lower() != PICTURE_SUFFIX:
            shutil.copy2(source, destination)
            continue
        with Image.open(source) as picture:
            if max(picture.size) <= edge:
                shutil.copy2(source, destination)
                continue
            picture.thumbnail((edge, edge), Image.Resampling.LANCZOS)
            picture.save(destination, optimize=True)
    return target


def exclusions() -> list[str]:
    """The Nuitka options leaving out what the application never loads."""
    return [f"--noinclude-dlls={pattern}" for pattern in UNUSED_QT_LIBRARIES] + [
        f"--nofollow-import-to={module}" for module in UNUSED_MODULES
    ]


def clean() -> None:
    """Remove previous output so nothing stale survives into this build."""
    for path in (NUITKA_DIST_DIR, BUNDLE_DIR):
        shutil.rmtree(path, ignore_errors=True)
    ONEFILE_EXE.unlink(missing_ok=True)
    PAYLOAD_DIR.mkdir(parents=True, exist_ok=True)


def command(version: str, onefile: bool) -> list[str]:
    """The whole Nuitka invocation."""
    numeric = pe_version(version)
    parts = [
        sys.executable,
        "-m",
        "nuitka",
        "--onefile" if onefile else "--standalone",
        "--assume-yes-for-downloads",
        "--enable-plugin=pyside6",
        # PyAV reaches this submodule at import time in a way Nuitka does not
        # follow, so a standalone build carries every one of its DLLs and then
        # dies on "No module named 'av.utils'" the first time a track needs
        # decoding. Measured by building a bundle that does nothing but import
        # av: without this it fails outright, with it the same bundle decodes,
        # seeks and resamples a real file. The whole package cannot be named
        # instead, since --include-package=av crashes Nuitka 4.2 with an
        # internal assertion.
        "--include-module=av.utils",
        f"--jobs={jobs()}",
        f"--windows-console-mode={console_mode()}",
        f"--output-dir={PAYLOAD_DIR}",
        f"--output-filename={EXE_NAME}.exe",
        f"--company-name={APP_AUTHOR}",
        f"--product-name={APP_DISPLAY_NAME}",
        f"--file-version={numeric}",
        f"--product-version={numeric}",
        # Windows reads this as the program's NAME: it is what Task Manager
        # lists a running process under and what the file's own properties
        # show as its description. The tagline used to sit here, so the
        # application announced itself as a sentence everywhere Windows asked
        # what it was. The name goes here; the tagline belongs on the site.
        f"--file-description={APP_DISPLAY_NAME}",
        f"--copyright={COPYRIGHT_NOTICE}",
    ]
    if ICON_FILE.exists():
        parts.append(f"--windows-icon-from-ico={ICON_FILE}")
    parts.extend(exclusions())
    if ASSETS_DIR.is_dir():
        staged = stage_assets(ASSET_STAGE_DIR)
        parts.append(f"--include-data-dir={staged}={ASSET_DESTINATION}")
    for item in DATA_FILES:
        if item.is_file():
            parts.append(f"--include-data-file={item}={item.name}")
    parts.append(str(ENTRY_SCRIPT))
    return parts


def settle_standalone() -> pathlib.Path | None:
    """Move Nuitka's main.dist output to a directory named after the app."""
    if not NUITKA_DIST_DIR.is_dir():
        return None
    shutil.rmtree(BUNDLE_DIR, ignore_errors=True)
    NUITKA_DIST_DIR.rename(BUNDLE_DIR)
    return BUNDLE_DIR / f"{EXE_NAME}.exe"


def report(target: pathlib.Path) -> None:
    """Say what was produced and how large it is."""
    if target.is_dir():
        size = sum(f.stat().st_size for f in target.rglob("*") if f.is_file())
    else:
        size = target.stat().st_size
    print(f"built {target}")
    print(f"size {size / BYTES_PER_MIB:.0f} MiB")


def main(argv: list[str] | None = None) -> int:
    """Build the application and report where it landed."""
    arguments = sys.argv[1:] if argv is None else argv
    onefile = STANDALONE_FLAG not in arguments
    require_nuitka()
    stamp_version.main()
    stamp_sitemap.main()
    version = read_version()
    shape = "onefile" if onefile else "standalone"
    print(f"{APP_DISPLAY_NAME} {version} ({shape}, {jobs()} jobs)")
    clean()
    result = subprocess.run(command(version, onefile), cwd=ROOT, check=False)
    if result.returncode != 0:
        print("Nuitka failed", file=sys.stderr)
        return result.returncode
    produced = ONEFILE_EXE if onefile else settle_standalone()
    if produced is None or not produced.exists():
        print("the build produced nothing where it was expected", file=sys.stderr)
        return 1
    report(ONEFILE_EXE if onefile else BUNDLE_DIR)
    return 0


if __name__ == "__main__":
    sys.exit(main())
