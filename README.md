# Stellody

A calm, local-first FLAC music player for a library you already own.

Stellody reads your music folder and never writes to it. Genres, ratings, play
counts and cached artwork live in Stellody's own store, so a bug in this
application cannot damage a file you spent years ripping and tagging.

## Who this is for

For someone with a large local FLAC library who wants it browsed, ordered and
played properly; someone who would rather have a small player that works than a
large one that does not.

Not for streaming, not for ripping CDs, not for syncing to devices and not for
managing a library by rewriting its tags. Stellody does none of those and is
not going to.

## What it does

- Scans a music folder you choose, then rescans incrementally when you add an
  album, without disturbing what is already there.
- Handles the common shapes a real library takes: one file per track, a single
  file per album with a sidecar cue sheet, multi-disc sets split across
  sibling folders, compilations and tracks with several credited artists.
- Reads cover art embedded in the files or sitting beside them.
- Shows the library as a grid of covers or as an ordered text view, sortable
  in either direction.
- Plays with an equalizer, shuffle, repeat and gapless track transitions.
- Reports damaged metadata instead of silently working around it, so you can
  repair it in a tagger of your choosing.

## What it deliberately does not do

- **It never writes to your music files.** This is enforced by a structural
  test, not by good intentions.
- It does not send anything to the internet. There is no cover lookup, no
  scrobbling and no telemetry.
- It does not encrypt anything at rest. The store holds library metadata, not
  secrets.

## Stack

| Concern | Choice |
|---|---|
| Language | Python 3.13 |
| Interface | PySide6 |
| Tags | mutagen |
| Decode | soundfile |
| Output | sounddevice |
| Buffers | numpy |
| Store | SQLite with FTS5 |

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

## Licence

Dual licensed. The model, meaning the domain, application and infrastructure
layers together with the build scripts, is under GPL-3.0. The user interface
layer is under LGPL-3.0, to align with Qt. See `LICENSE` for the mapping.
