# Development

How to build Stellody on each platform and cut a release.
What it does is in [`README.md`](README.md); how it is put together is in
[`ARCHITECTURE.md`](ARCHITECTURE.md); how it is tested is in
[`TESTING.md`](TESTING.md).

## Tools

The product's stack is the table in [`README.md`](README.md#stack). What a
developer meets beyond it:

| Concern | Choice |
|---|---|
| Decode routing | PyAV takes the suffixes in `PACKET_SUFFIXES`; soundfile the rest |
| Device lists | Windows' endpoint enumeration (ctypes over COM) on Windows, Qt Multimedia elsewhere; on Linux a chosen device is reached through PortAudio's `pulse` device with `PULSE_SINK` |
| Buffers | numpy |
| Checks | black, flake8, ruff, pytest, pytest-cov, pytest-qt |
| Icons and the shipped assets | Pillow, a build dependency of every build |

`requirements.txt` pins the runtime exactly, so a build of one commit is the
same build whenever it is made; `tests/structural/test_environment.py` fails
when an installed version differs from its pin. `requirements-dev.txt` reads
it then adds the tools with floors.

## Running from source

The commands are under Running from source in [`README.md`](README.md). The
venv must be named `venv` at the repository root; `gate.ps1` runs every check
with `venv\Scripts\python.exe`. The logs and where they live are under Your
privacy in the same file.

## Building

Each platform builds on itself; none cross-compiles. `buildexe.py`,
`buildinstaller.py` and `builddmg.py` stop before compiling unless the
installed Nuitka is at least `NUITKA_MINIMUM` and below `NUITKA_CEILING`
(`buildexe.py`); `requirements-dev.txt` holds the same range.

**What every build ships.** No build ships `assets/` itself. `stage_assets` in
`buildexe.py` writes a copy into `installer/payload/assets-stage`, leaving out
`OTHER_PLATFORM_ASSETS` and writing each PNG larger than `icon_edge_px()` on
its longer side at that size: the largest icon (`ICON_PX`) at
`INTERFACE_SCALE` times `WINDOWS_MAX_DISPLAY_SCALE`. Both constants are read
from the source by `source_constant` rather than imported, so staging needs
Pillow alone; that makes Pillow a build dependency on every platform.
`exclusions()` in the same file adds `--noinclude-dlls` for each pattern in
`UNUSED_QT_LIBRARIES` and `--nofollow-import-to` for each package in
`UNUSED_MODULES`; the application, setup program and macOS builds all pass it
to Nuitka.

**Windows**

```powershell
python buildexe.py
python buildinstaller.py
```

`buildexe.py` stamps the site (below), stages the assets, then compiles the
application with Nuitka into one file using every core; `--standalone` gives a
directory bundle instead, quicker to inspect. `buildinstaller.py` stamps the
site, stages the built application as a zipped payload, then compiles the
setup program around it into `dist-installer\StellodySetup.exe`. The setup
program carries only `SETUP_ASSETS`, the four pictures it draws, staged by the
same `stage_assets`. Everything the setup program writes is per user.

**macOS**

```
python builddmg.py
```

In order: checks the platform and dependencies; stages the assets and checks
everything the bundle names is on disk; checks the notarization credentials;
stamps the site; compiles with Nuitka; checks the bundle carries what it was
given and moves that data into `Contents/Resources`; strips the object files
PySide6 ships inside its QML plugins; signs and notarizes the application then
staples it; builds the disk image, sets its icons, signs, notarizes, staples
and verifies it. The credential is a keychain profile stored once with
`xcrun notarytool store-credentials Stellody`; `ALLOW_UNNOTARIZED=1` skips
notarizing for local testing only.

**Linux**

```
./build_flatpak.sh
./clean_flatpak.sh
```

The build fetches wheels and source archives first. It stages the assets in a
throwaway environment holding Pillow alone (`.flatpak-stage-venv`, at the
version `requirements-dev.txt` names), then builds offline, compiling
PortAudio and the Kerberos client library into the bundle since the runtime
carries neither. The staged folder ships as the application's assets; the
launcher icons are installed from `assets/`. It produces `stellody.flatpak`.
The cleaner uninstalls the application and removes what the build wrote at
the repository root; the staged assets under `installer/payload/` stay.
`--purge-data` also removes the listener's data.

## Generated assets

- **Icons.** `python generate_icons.py` derives every icon in `assets/` and the
  site's favicons from `assets/application-icon.png`.
- **Site version tokens and asset hashes.** `stamp_version.py` writes `VERSION`
  into each version token under `docs/` and puts a content hash on each local
  stylesheet and script link.
- **Sitemap dates.** `stamp_sitemap.py` dates each page in `docs/sitemap.xml`
  from the last commit that touched it.

The Windows and macOS builds run both stamps; the Flatpak build runs neither,
so after a bump made without those builds run them directly:

```powershell
python stamp_version.py
python stamp_sitemap.py
```

`docs/` is served by GitHub Pages from `main` at
[stellody.co.uk](https://stellody.co.uk/); pushing `main` publishes it. Each
page carries the GoatCounter tags in its head.

## Versioning

`VERSION` is the only home of the version string. The application reads it at
start (`stellody/shared/version.py`), the builds read it and the site is
stamped from it; no markdown file carries one. A bump is owed against the
newest tag, so a `VERSION` already ahead of the tag has had its bump.

## Cutting a release

1. The gate is green (`.\gate.ps1`, exit code zero).
2. The release notes are written in `NOTES.md`, which is ignored by git and
   holds the pending release alone.
3. The tag and the GitHub release are Oliver's to make.
