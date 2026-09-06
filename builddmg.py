#!/usr/bin/env python3
"""macOS DMG builder for Stellody.

Requires macOS with Xcode command-line tools and Homebrew.
Run from the repository root with the venv active:
    python builddmg.py

Notarization is mandatory. A Developer ID signature alone is not enough: since
macOS 10.15 Gatekeeper rejects signed-but-unnotarized apps with "Apple could not
verify ... is free of malware". Credentials come from this app's keychain
profile (NOTARY_PROFILE), stored once with `xcrun notarytool store-credentials`,
so nothing needs to be exported to run a release build.

The application is compiled with Nuitka, which is what the Windows build uses.
One toolchain across both platforms means one set of packaging surprises rather
than two; the PyAV workaround below is needed on each of them.

Env vars:
    APPLE_KEYCHAIN_PROFILE    : override the per-app keychain profile
    APPLE_ID                  : Apple ID, for CI that has no keychain
    APPLE_APP_PASSWORD        : app-specific password, paired with APPLE_ID
    DEVELOPER_ID_APPLICATION  : override the default signing identity
    APPLE_TEAM_ID             : Team ID for notarization (defaults to W7K465GKFJ)
    ALLOW_UNNOTARIZED         : set to 1 to build without notarizing. The result
                                is for local testing only and must never be
                                published as a release artifact.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tempfile
from importlib import metadata
from pathlib import Path

from packaging.requirements import InvalidRequirement, Requirement

import stamp_sitemap
import stamp_version
from build_utils import require, run, section
from dmg_icon import set_volume_icon

# The copyright notice comes from the package rather than being written here as
# well, exactly as the Windows build reads it: the bundle's metadata and the
# About box have to say the same thing, so they read the same constant.
from stellody.shared.version import COPYRIGHT_NOTICE

ROOT = Path(__file__).resolve().parent
DEV_VERSION = "0.0.0-dev"


def _read_version() -> str:
    version_file = ROOT / "VERSION"
    if version_file.exists():
        return version_file.read_text(encoding="utf-8").strip() or DEV_VERSION
    return DEV_VERSION


# -- Constants ----------------------------------------------------------------

APP_NAME = "Stellody"
APP_VERSION = _read_version()
BUNDLE_ID = "uk.codecrafter.Stellody"
FINAL_DMG = "stellody.dmg"
RW_DMG = "_stellody_rw.dmg"
VOLUME_NAME = f"Install {APP_NAME}"

ENTRY_SCRIPT = ROOT / "main.py"
DIST_DIR = ROOT / "dist"
STAGING_DIR = "_dmg_staging"

# Written by generate_icons.py from the master artwork, which is the one place
# any icon in this project comes from. Read rather than derived here.
ICNS_FILE = ROOT / "assets" / "stellody.icns"
FILE_ICON_PNG = ROOT / "assets" / "stellody_icon_1024.png"

# Directories shipped whole, as (source, destination inside the bundle); loose
# files shipped at its root. The same two lists the Windows build uses.
DATA_DIRS: tuple[tuple[Path, str], ...] = ((ROOT / "assets", "assets"),)
DATA_FILES: tuple[Path, ...] = (
    ROOT / "VERSION",
    ROOT / "LICENSE",
    ROOT / "LICENSE-GPL-3.0.txt",
    ROOT / "LICENSE-LGPL-3.0.txt",
)

DEVELOPER_ID = os.environ.get(
    "DEVELOPER_ID_APPLICATION",
    "Developer ID Application: Oliver Ernster (W7K465GKFJ)",
)
APPLE_ID = os.environ.get("APPLE_ID", "")
APPLE_APP_PASSWORD = os.environ.get("APPLE_APP_PASSWORD", "")
APPLE_TEAM_ID = os.environ.get("APPLE_TEAM_ID", "W7K465GKFJ")

# The notarization credential for this app, created once with
#   xcrun notarytool store-credentials Stellody \
#     --apple-id <id> --team-id <team> --password <app-specific>
# One profile per app means a leaked credential can be revoked for a single
# app. Stated explicitly rather than derived from a display name: the profile
# is a fact registered with Apple; deriving it would silently change which
# credential the build looks for if that name were ever edited.
# APPLE_KEYCHAIN_PROFILE overrides it.
NOTARY_PROFILE = os.environ.get("APPLE_KEYCHAIN_PROFILE", "") or APP_NAME

# The notary service accepts only an app-specific password from appleid.apple.com
# and rejects the Apple account password with HTTP 401. The shape is distinctive,
# so it is checked before the build rather than discovered after it.
APP_SPECIFIC_PASSWORD_RE = re.compile(r"^[a-z]{4}-[a-z]{4}-[a-z]{4}-[a-z]{4}$")

# Escape hatch for local test builds. Distribution builds must never set this:
# an unnotarized DMG is rejected by Gatekeeper on every machine but the one that
# signed it; the failure is invisible at build time.
ALLOW_UNNOTARIZED = os.environ.get("ALLOW_UNNOTARIZED", "") == "1"

# Notarization is the default and the keychain profile always resolves, so the
# only way to skip it is to ask for that explicitly.
NOTARIZING = not ALLOW_UNNOTARIZED

BYTES_PER_MIB = 1024 * 1024
CREATE_DMG_OK = (0, 2)  # 2 means it could not set a window background, headless

# Minimal hardened-runtime entitlements. Stellody decodes and plays audio, has
# no JIT and reaches the network only for its update check, which needs no
# entitlement outside the sandbox. disable-library-validation lets the hardened
# runtime load the bundled Qt frameworks signed with our identity.
ENTITLEMENTS = """\
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>com.apple.security.cs.disable-library-validation</key>
    <true/>
</dict>
</plist>
"""


# -- Steps --------------------------------------------------------------------


def check_platform() -> None:
    section("Platform check")
    if sys.platform != "darwin":
        sys.exit("ERROR: This script must run on macOS.")
    result = subprocess.run(
        ["sw_vers", "-productVersion"], capture_output=True, text=True, check=False
    )
    print(f"  macOS {result.stdout.strip()}")
    if not shutil.which("python3"):
        sys.exit("ERROR: no python3 on PATH.")
    require("create-dmg", "create-dmg")
    require("codesign")
    print("  All tools present.")


def check_notarization_credentials() -> None:
    """Fail before the build starts if the release cannot be notarized.

    Checked up front rather than at the notarization step so a missing password
    costs seconds instead of a full compile.
    """
    section("Notarization credentials")
    if ALLOW_UNNOTARIZED:
        print("  WARNING: ALLOW_UNNOTARIZED=1 set.")
        print("  WARNING: this build is for local testing and must not be released.")
        return
    if APPLE_ID and APPLE_APP_PASSWORD:
        if not APP_SPECIFIC_PASSWORD_RE.match(APPLE_APP_PASSWORD):
            sys.exit(
                "ERROR: APPLE_APP_PASSWORD is not an app-specific password.\n"
                "  Expected four lowercase groups of four, like abcd-efgh-ijkl-mnop.\n"
                "  An Apple account password is rejected by the notary service with\n"
                "  'HTTP status code: 401. Invalid credentials'.\n"
                "  Generate one at https://appleid.apple.com (Sign-In and Security,\n"
                "  App-Specific Passwords); or leave both variables unset and store\n"
                f"  the credential in the keychain as profile {NOTARY_PROFILE}."
            )
        print(f"  Notarizing as {APPLE_ID} (team {APPLE_TEAM_ID}).")
        return
    print(f"  Notarizing with keychain profile {NOTARY_PROFILE}.")


def check_runtime_dependencies() -> None:
    """Fail if anything in requirements.txt is absent from the build interpreter.

    A packager only warns when it cannot find a package, so a stale venv yields
    a bundle that builds, signs and notarizes cleanly then dies at launch with
    ModuleNotFoundError. Checking the interpreter that is about to be compiled
    turns a silent runtime failure into a build failure. The suite asserts the
    same thing, in tests/structural/test_environment.py; it is repeated here
    because a build is not required to have run the suite first.
    """
    section("Runtime dependencies")
    requirements = ROOT / "requirements.txt"
    if not requirements.exists():
        sys.exit(f"ERROR: {requirements.name} not found beside builddmg.py.")

    missing: list[str] = []
    checked = 0
    for raw in requirements.read_text(encoding="utf-8").splitlines():
        line = raw.split("#")[0].strip()
        if not line or line.startswith("-"):
            continue
        try:
            requirement = Requirement(line)
        except InvalidRequirement as error:
            sys.exit(f"ERROR: cannot parse '{line}' in {requirements.name}: {error}")
        if requirement.marker is not None and not requirement.marker.evaluate():
            continue
        checked += 1
        try:
            metadata.version(requirement.name)
        except metadata.PackageNotFoundError:
            missing.append(requirement.name)

    if missing:
        sys.exit(
            "ERROR: the build interpreter is missing "
            f"{len(missing)} of {checked} requirements:\n"
            + "".join(f"    {name}\n" for name in missing)
            + "  The build would omit them and the app would crash at launch\n"
            "  with ModuleNotFoundError. Install them first:\n"
            f"    pip install -r {requirements.name}"
        )
    print(f"  All {checked} requirements present.")


def check_bundled_assets() -> None:
    """A named asset that is not on disk FAILS the build rather than being skipped.

    Skipping produces a bundle that launches perfectly with controls wearing no
    pictures, discoverable only by running the packaged application and looking,
    while the build itself reports success. An asset named here and absent is a
    mistake in one place or the other; either way it is not shippable.
    """
    section("Bundled assets")
    missing = [str(path) for path in DATA_FILES if not path.is_file()]
    missing += [str(source) for source, _dest in DATA_DIRS if not source.is_dir()]
    if not ICNS_FILE.is_file():
        missing.append(f"{ICNS_FILE} (run: python generate_icons.py)")
    if missing:
        sys.exit(
            "ERROR: these are named for the bundle but not on disk:\n  "
            + "\n  ".join(missing)
        )
    print(f"  {len(DATA_FILES)} file(s), {len(DATA_DIRS)} directory tree(s), icon.")


def notarytool_credentials() -> list[str]:
    """Authentication arguments for notarytool.

    An explicit APPLE_ID and APPLE_APP_PASSWORD pair wins, for CI that has no
    keychain. Otherwise the per-app profile is used, which keeps the secret out
    of the process arguments where any other process could read it via ps.
    """
    if APPLE_ID and APPLE_APP_PASSWORD:
        return [
            "--apple-id",
            APPLE_ID,
            "--password",
            APPLE_APP_PASSWORD,
            "--team-id",
            APPLE_TEAM_ID,
        ]
    return ["--keychain-profile", NOTARY_PROFILE]


def redact(cmd: list[str]) -> str:
    """Render a command with the value after --password masked.

    build_utils.run echoes every command it runs; CalledProcessError repeats
    the whole argument list in its traceback. Both would otherwise copy the
    app-specific password into build logs and CI output.
    """
    parts: list[str] = []
    mask_next = False
    for arg in (str(item) for item in cmd):
        parts.append("********" if mask_next else arg)
        mask_next = arg == "--password"
    return " ".join(parts)


def notarytool_submit(target: Path) -> None:
    """Submit target to Apple and wait for the verdict.

    A failed submission stops the build rather than producing an artifact that
    looks distributable. subprocess is called directly instead of through run()
    so that neither the echoed command nor the failure path exposes the
    password. Stapling is a separate step because the submitted file and the
    file that carries the ticket differ for a .app (a zip is submitted, the
    bundle is stapled).
    """
    cmd = [
        "xcrun",
        "notarytool",
        "submit",
        str(target),
        *notarytool_credentials(),
        "--wait",
    ]
    print(f"  $ {redact(cmd)}")
    if subprocess.run(cmd, check=False).returncode == 0:
        return
    sys.exit(
        "ERROR: notarization failed (notarytool output above).\n"
        "  'No Keychain password item found' means this app has no stored\n"
        "  credential yet. Generate an app-specific password at\n"
        "  https://appleid.apple.com (Sign-In and Security), then:\n"
        f"    xcrun notarytool store-credentials {NOTARY_PROFILE} \\\n"
        "      --apple-id you@example.com --team-id "
        f"{APPLE_TEAM_ID} --password <app-specific>\n"
        "  'HTTP status code: 401' means the credential is wrong: use an\n"
        "  app-specific password, not your Apple account password.\n"
        "  For an 'Invalid' verdict, the per-binary reasons are in:\n"
        "    xcrun notarytool log <submission-id> "
        f"--keychain-profile {NOTARY_PROFILE}"
    )


def clean() -> None:
    section("Clean previous build")
    for name in ["build", "dist", FINAL_DMG, STAGING_DIR, RW_DMG]:
        path = ROOT / name
        if not path.exists():
            continue
        if path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink()
        print(f"  Removed: {name}")


def build_app_bundle() -> Path:
    """Compile the application into a .app bundle with Nuitka.

    Nuitka names the bundle after the entry script rather than after the
    application, so what it produces is found by looking rather than by being
    told, then moved to the name everything after this expects.
    """
    section("Nuitka: build .app bundle")

    cmd = [
        sys.executable,
        "-m",
        "nuitka",
        "--standalone",
        "--macos-create-app-bundle",
        "--assume-yes-for-downloads",
        "--enable-plugin=pyside6",
        # PyAV reaches this submodule at import time in a way Nuitka does not
        # follow, so a standalone build carries every one of its libraries and
        # then dies on "No module named 'av.utils'" the first time a track
        # needs decoding. Measured on the Windows build; the same flag is
        # needed here because it is a property of PyAV rather than of Windows.
        "--include-module=av.utils",
        f"--jobs={os.cpu_count() or 1}",
        f"--macos-app-name={APP_NAME}",
        f"--macos-app-version={APP_VERSION}",
        f"--macos-app-icon={ICNS_FILE}",
        f"--macos-signed-app-name={BUNDLE_ID}",
        f"--copyright={COPYRIGHT_NOTICE}",
        f"--output-dir={DIST_DIR}",
    ]
    for source, destination in DATA_DIRS:
        cmd.append(f"--include-data-dir={source}={destination}")
    for item in DATA_FILES:
        cmd.append(f"--include-data-file={item}={item.name}")
    cmd.append(str(ENTRY_SCRIPT))

    run(cmd)

    produced = sorted(DIST_DIR.glob("*.app"))
    if not produced:
        sys.exit(f"ERROR: Nuitka produced no .app bundle in {DIST_DIR}")
    app_path = DIST_DIR / f"{APP_NAME}.app"
    if produced[0] != app_path:
        if app_path.exists():
            shutil.rmtree(app_path)
        produced[0].rename(app_path)
    print(f"  Built: {app_path}")
    return app_path


def strip_build_artifacts(app_path: Path) -> None:
    section("Strip build artifacts")
    # PySide6 ships .cpp.o object files inside its QML plugin directories.
    # They are Mach-O relocatable binaries that codesign --deep silently skips
    # but Gatekeeper flags as unsigned, causing the entire bundle to be rejected.
    removed = 0
    for found in app_path.rglob("*.o"):
        if found.is_file():
            found.unlink()
            removed += 1
    for directory in sorted(app_path.rglob("objects-*"), reverse=True):
        if directory.is_dir() and not any(directory.iterdir()):
            directory.rmdir()
    print(f"  Removed {removed} intermediate object file(s)")


def sign_bundle(app_path: Path, entitlements_path: Path) -> None:
    section("Code signing")
    run(
        [
            "codesign",
            "--force",
            "--deep",
            "--options",
            "runtime",
            "--entitlements",
            str(entitlements_path),
            "--sign",
            DEVELOPER_ID,
            str(app_path),
        ]
    )
    run(["codesign", "--verify", "--deep", "--strict", str(app_path)])
    print("  Signature verified.")


def notarize_bundle(app_path: Path) -> None:
    """Notarize and staple the .app before it is placed in the DMG.

    Stapling only the DMG leaves the copied-out .app with no local ticket, so
    Gatekeeper falls back to an online check and the app fails to launch for a
    user who is offline or behind a restrictive network. notarytool only accepts
    archives, so the bundle is zipped with ditto first (ditto preserves the
    symlinks and metadata the embedded signature depends on); the ticket is then
    stapled to the bundle itself, since a zip cannot carry one.
    """
    if not NOTARIZING:
        return
    section("Notarize .app bundle")
    with tempfile.TemporaryDirectory() as tmp:
        archive = Path(tmp) / f"{APP_NAME}.zip"
        run(["ditto", "-c", "-k", "--keepParent", str(app_path), str(archive)])
        notarytool_submit(archive)
    run(["xcrun", "stapler", "staple", str(app_path)])
    print("  Bundle notarized and stapled.")


def create_dmg(app_path: Path) -> None:
    section("Create DMG")

    staging = ROOT / STAGING_DIR
    staging.mkdir(exist_ok=True)
    dest = staging / app_path.name
    if dest.exists():
        shutil.rmtree(dest)
    # ditto preserves the symlinks macOS frameworks rely on (e.g.
    # Python.framework/Python -> Versions/Current/Python). Dereferencing them
    # into regular files invalidates every embedded code signature and causes
    # dlopen failures at runtime.
    run(["ditto", str(app_path), str(dest)])

    final = ROOT / FINAL_DMG
    final.unlink(missing_ok=True)

    cmd = [
        "create-dmg",
        "--volname",
        VOLUME_NAME,
        "--window-pos",
        "200",
        "120",
        "--window-size",
        "640",
        "400",
        "--icon-size",
        "100",
        "--text-size",
        "14",
        "--app-drop-link",
        "520",
        "180",
        "--icon",
        f"{APP_NAME}.app",
        "120",
        "180",
        str(final),
        str(dest),
    ]

    result = run(cmd, check=False)
    if result.returncode not in CREATE_DMG_OK:
        sys.exit(f"ERROR: create-dmg failed (exit {result.returncode})")

    shutil.rmtree(staging)
    print(f"  DMG created: {FINAL_DMG}")


def sign_dmg() -> None:
    section("Sign DMG")
    run(["codesign", "--force", "--sign", DEVELOPER_ID, str(ROOT / FINAL_DMG)])
    print("  DMG signed.")


def notarize_dmg() -> None:
    if not NOTARIZING:
        return
    section("Notarize DMG")
    notarytool_submit(ROOT / FINAL_DMG)
    run(["xcrun", "stapler", "staple", str(ROOT / FINAL_DMG)])
    print("  Notarization complete and stapled.")


def verify_dmg() -> None:
    section("Verify DMG")
    final = ROOT / FINAL_DMG
    run(["codesign", "--verify", str(final)])
    size_mib = final.stat().st_size / BYTES_PER_MIB
    if not NOTARIZING:
        print(f"  {FINAL_DMG}  ({size_mib:.1f} MiB): UNNOTARIZED, local testing only")
        return
    # stapler validate proves a ticket is attached; spctl replays the check
    # Gatekeeper performs on the end user's machine. Together they catch the
    # silent case where signing succeeded but notarization never happened.
    run(["xcrun", "stapler", "validate", str(final)])
    run(["spctl", "--assess", "--type", "install", "-vv", str(final)])
    print(f"  {FINAL_DMG}  ({size_mib:.1f} MiB): notarized, ready for distribution")


def apply_file_icon() -> None:
    section("Apply file icon")
    require("fileicon")
    run(["fileicon", "set", str(ROOT / FINAL_DMG), str(FILE_ICON_PNG)])
    print(f"  Icon applied to {FINAL_DMG}")


# -- Main ---------------------------------------------------------------------


def main() -> int:
    print(f"\nSTELLODY DMG BUILDER  v{APP_VERSION}")
    print(f"Signing identity: {DEVELOPER_ID}")

    check_platform()
    check_runtime_dependencies()
    check_bundled_assets()
    check_notarization_credentials()
    stamp_version.main()
    stamp_sitemap.main()
    clean()

    with tempfile.NamedTemporaryFile(
        suffix=".entitlements", mode="w", delete=False
    ) as handle:
        handle.write(ENTITLEMENTS)
        entitlements_path = Path(handle.name)

    try:
        app_path = build_app_bundle()
        strip_build_artifacts(app_path)
        sign_bundle(app_path, entitlements_path)
        notarize_bundle(app_path)
        create_dmg(app_path)
        # Both icon steps rewrite the DMG, so they run before it is signed
        # and notarized. Doing either afterwards would modify a file that
        # Gatekeeper has already been told the hash of.
        set_volume_icon(ICNS_FILE, str(ROOT / FINAL_DMG), str(ROOT / RW_DMG))
        apply_file_icon()
        sign_dmg()
        notarize_dmg()
        verify_dmg()
    finally:
        entitlements_path.unlink(missing_ok=True)

    print(f"\nDone.  Distribute: {FINAL_DMG}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
