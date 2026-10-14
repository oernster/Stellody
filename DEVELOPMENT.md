# Development

How to build Stellody on each platform and cut a release.
What it does is in [`README.md`](README.md); how it is put together is in
[`ARCHITECTURE.md`](ARCHITECTURE.md); how it is tested is in
[`TESTING.md`](TESTING.md).

## Tools

| Concern | Choice |
|---|---|
| Language | Python 3.13 |
| Interface | PySide6 |
| Tags | mutagen |
| Decode | soundfile, plus PyAV for the suffixes in `PACKET_SUFFIXES` |
| Output | sounddevice over PortAudio; device lists from Windows' endpoint enumeration (ctypes over COM) on Windows and Qt Multimedia elsewhere; on Linux a chosen device is reached through PortAudio's `pulse` device with `PULSE_SINK` |
| Buffers | numpy |
| Store | SQLite |
| Checks | black, flake8, ruff, pytest, pytest-cov, pytest-qt |
| Packaging | Nuitka on Windows and macOS; Flatpak on Linux |
| Icons | Pillow |

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

Each platform builds on itself; none cross-compiles.

**Windows**

```powershell
python buildexe.py
python buildinstaller.py
```

`buildexe.py` stamps the site (below), then compiles the application with
Nuitka into one file using every core; `--standalone` gives a directory bundle
instead, quicker to inspect. `buildinstaller.py` stamps the site, stages the
built application as a zipped payload, then compiles the setup program around
it into `dist-installer\StellodySetup.exe`. Everything the setup program writes
is per user.

**macOS**

```
python builddmg.py
```

In order: checks the platform, dependencies, bundled assets and notarization
credentials; stamps the site; compiles with Nuitka; strips the object files
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

The build fetches wheels and source archives first, then builds offline,
compiling PortAudio and the Kerberos client library into the bundle since the
runtime carries neither. It produces `stellody.flatpak`. The cleaner undoes
what the build wrote; `--purge-data` also removes the listener's data.

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
