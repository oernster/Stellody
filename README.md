# <img width="128" height="128" alt="application-icon" src="https://github.com/user-attachments/assets/856669d1-6207-4f38-8ed6-816c6b05a40f" /> Stellody

A calm, local-first music player for a library you already own.

Stellody reads your music folder and never writes to it. What it learns about
your library, the problems it finds in your tags and your own settings live in
Stellody's own store, so a bug in this application cannot damage a file you
spent years ripping and tagging.

## Who this is for

For someone with a large local music library who wants it browsed, ordered and
played properly; someone who would rather have a small player that works than a
large one that does not.

Not for streaming, not for ripping CDs, not for syncing to devices and not for
managing a library by rewriting its tags. Stellody does none of those and is
not going to.

## What it does

- Scans a music folder you choose, then rescans incrementally when you add an
  album: a folder whose files are all unchanged is reused without opening one.
- Handles the common shapes a real library takes: one file per track, a single
  file per album with a sidecar cue sheet, multi-disc sets split across
  sibling folders, compilations and tracks with several credited artists.
- Shows the library as albums, discs and tracks, ordered either way.
- Plays a track chosen by double click, by Return or from the right click
  menu, then works through the album on its own.
- Offers previous, play and pause, stop and next, both on the tray and on that
  menu, with the library highlight following whatever is playing. Back returns
  to the beginning of the track in hand and waits there; pressing it again from
  there goes to the track before, waiting at its beginning too.
- Carries volume, mute, shuffle and repeat, each remembered between sessions.
  Shuffle leads its scattered run with the track already playing, so next
  reaches the whole of the rest of the album. Repeat plays the album again
  rather than the track, scattering it afresh each time round when shuffle is
  on.
- Reports damaged metadata instead of silently working around it, so you can
  repair it in a tagger of your choosing.
- Reaches everything from the keyboard, in the order the window is drawn.
- Runs in the system tray and can start there. Opening Stellody again while
  it is already running brings that window back rather than starting a
  second copy.
- Offers to buy the author a drink, which opens a donation page in your
  browser.

Stellody is early. Cover art, a grid view, search, ratings, play counts, an
equalizer, gapless transitions and accepting the repairs the health report
describes are not built; `PLAN.md` lists what is still to come and what is
deliberately excluded. Where a control for one of those is already on screen it
is disabled and says so.

## What it deliberately does not do

- **It never writes to your music files.** This is enforced by a structural
  test, not by good intentions.
- It does not send anything to the internet. There is no cover lookup, no
  scrobbling, no telemetry and no update check. The one outward thing it does
  is hand a donation link to your browser when you press the button for it;
  the browser does the asking, never Stellody.
- It does not encrypt anything at rest. The store holds library metadata, not
  secrets.

## Stack

| Concern | Choice |
|---|---|
| Language | Python 3.13 |
| Interface | PySide6 |
| Tags | mutagen |
| Decode | soundfile |
| Output | sounddevice, on WASAPI |
| Buffers | numpy |
| Store | SQLite |

## Running from source

```
python -m pip install -r requirements-dev.txt
python main.py
```

## Tests

```
python -m pytest
```

The suite gates at 100% branch coverage over the domain and application
layers; it fails the build below that. It also runs black, flake8 and ruff as
assertions, so a formatting or linting regression is a test failure.

## Building

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

Windows is the only platform built today.

## Licence

Dual licensed. The model, meaning the domain, application and infrastructure
layers together with the build scripts, is under GPL-3.0. The user interface
layer is under LGPL-3.0, to align with Qt. See `LICENSE` for the mapping.
