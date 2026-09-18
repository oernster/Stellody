# Development

How to run Stellody from source, test it, build it on each platform and
publish its website. What the product does and why is in
[`README.md`](README.md); how it is put together is in
[`ARCHITECTURE.md`](ARCHITECTURE.md).

## Stack

| Concern | Choice |
|---|---|
| Language | Python 3.13 |
| Interface | PySide6 |
| Tags | mutagen |
| Decode | soundfile, plus PyAV for M4A, WMA, WavPack and AAC |
| Output | sounddevice over PortAudio: WASAPI on Windows, CoreAudio on macOS, the system mixer on Linux; Qt Multimedia notices the output device changing |
| Buffers | numpy |
| Store | SQLite |

## Running from source

```
python -m pip install -r requirements-dev.txt
python main.py
```

**The runtime is pinned; the tools are not.** `requirements.txt` names exact
versions, because a build of one commit has to be the same build whenever it is
made. `requirements-dev.txt` reads it before adding the tools, black, flake8,
ruff, pytest and Nuitka among them, which keep their floors, since a linter
moving forward changes the checks rather than what is shipped. Upgrading a
pinned package therefore fails the suite until the pin is moved to match, naming
the package and both versions; that is the guard working rather than a fault.

## Tests

```
.\gate.ps1
```

That runs the formatter, both linters and the suite against the project's own
virtual environment. The suite gates at 100% branch coverage over the domain
and application layers. [`TESTING.md`](TESTING.md) says how to read the result,
the rules a run by hand has to follow and how a new test or guard is written.

## Building

Each platform builds on itself; none of the three cross-compiles.

**Windows:**

```
python buildexe.py
python buildinstaller.py
```

The first compiles the application with Nuitka into a single file, using every
core the machine has. The second zips that file as a payload and compiles the
setup program around it, producing `dist-installer/StellodySetup.exe`.

Everything the setup program writes is per user, so Windows never asks for
administrator rights. Pass `--standalone` to the first script for a directory
bundle instead, which is quicker to inspect when a build misbehaves.

**macOS:**

```
python builddmg.py
```

Compiles with Nuitka as the Windows build does, strips the object files PySide6
ships inside its QML plugins, signs with a Developer ID, then notarizes both
the application and the image before stapling each. Notarization is not
optional: Gatekeeper rejects a signed but unnotarized application, so the
credential comes from a keychain profile stored once with
`xcrun notarytool store-credentials Stellody`. `ALLOW_UNNOTARIZED=1` builds
without it, for local testing only.

**Linux:**

```
./build_flatpak.sh
./clean_flatpak.sh
```

The wheels and the source archives are fetched to the host first, so the build
itself reaches the network for nothing. PortAudio is compiled from source into
the bundle, because the sounddevice wheel carries a library for Windows and
macOS only while the freedesktop runtime ships none. So is the Kerberos client
library, which Qt's network module links while the runtime carries none. The
cleaner uninstalls Stellody then removes what the build wrote and nothing else;
pass `--purge-data` to remove your ratings, play counts, stated tags and
accepted corrections as well.

## The website

`docs/` is the site, served by GitHub Pages at
[stellody.co.uk](https://stellody.co.uk/), which is the canonical host. Version
tokens in it are stamped from `VERSION` by `stamp_version.py`, which the Windows
and macOS build scripts call, so the site is never hand-versioned. The Flatpak
build does not stamp the site; run the script directly after a bump made
without building on either of the other two.

The same pages are also served at `stellody.com`, out of the
[stellody-website](https://github.com/oernster/stellody-website) repository
under `public/`. **That mirror keeps itself up to date and needs nothing from
you.** Pushing a change to `docs/` runs `.github/workflows/mirror-site.yml`,
which carries it across, pushes it then asks Render to deploy it. Commit here
and both hosts follow.

**The deploy is asked for rather than inferred, deliberately.** Render's own
Auto-Deploy is set to On Commit, yet it stopped hearing pushes with nothing
anywhere saying so; deploys went out only when somebody pressed for one. The
workflow already knows a deploy is wanted, so it says so outright, through a
deploy hook held as `RENDER_DEPLOY_HOOK`. Without that secret the mirror still
updates while stellody.com waits; the run then logs a warning saying exactly
that.

One trap is worth knowing before investigating either host. A browser holding
the previous page is indistinguishable from a deploy that never ran, so hard
refresh first.

`sync_site.py` is what the workflow runs. It works locally too:

```
python sync_site.py           # carry docs/ across to ../stellody-website/public
python sync_site.py --check   # report drift, write nothing, exit 1 if any
```

Two files are deliberately NOT mirrored. `docs/CNAME` names the Pages custom
domain and means nothing on Render; `docs/sitemap.xml` stays because this host
owns the sitemap. `robots.txt` differs on the mirror on purpose, so it is
neither copied over nor deleted there. The mirrored pages keep their
`canonical`, `og:url` and `og:image` pointing here, which is what stops the two
hosts competing for the same pages.

The workflow reads two secrets. `MIRROR_TOKEN` is a fine-grained personal access
token scoped to `oernster/stellody-website` alone, with Contents set to read
and write; without it the run stops at once. `RENDER_DEPLOY_HOOK` is the deploy
hook described above.
