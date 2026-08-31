# <img width="128" height="128" alt="application-icon" src="https://github.com/user-attachments/assets/856669d1-6207-4f38-8ed6-816c6b05a40f" /> Stellody

A calm, local-first FLAC player for a library you already own.

Stellody reads your music folder and never writes to it. What it learns about
your library, the problems it finds in your tags and your own settings live in
Stellody's own store, so a bug in this application cannot damage a file you
spent years ripping and tagging.

## Who this is for

For someone with a large local music library who wants it browsed, ordered and
played properly; someone who would rather have a small player that works than a
large one that does not.

Stellody reads FLAC and nothing else today, so a folder of MP3, M4A or WMA
scans to nothing. Measured over the library it is developed against, that hides
146 of the 656 folders holding audio and part of 23 more, most of them M4A.
`PLAN.md` milestone 11 is the work that widens it and sizes both halves of it.

Not for streaming, not for ripping CDs, not for syncing to devices and not for
managing a library by rewriting its tags. Stellody does none of those and is
not going to.

## What it does

- Scans a music folder you choose, then rescans incrementally when you add an
  album: a folder whose files are all unchanged is reused without opening one.
- Handles the common shapes a real library takes: one file per track, a single
  file per album with a sidecar cue sheet, multi-disc sets split across
  sibling folders, a bonus disc whose folder names no number among them,
  compilations and tracks with several credited artists.
- Shows the library as albums, discs and tracks, ordered either way, else as
  a grid of covers with a toggle at the left of the bottom strip between the two.
  Picking a sleeve opens that album underneath the grid, its tracks running down
  two columns with the first ready to play, so the sleeves stay where they were;
  picking the same sleeve again rolls that pane back up. The sleeves are drawn
  at three sizes, cycled from the bottom strip. The view and the size are both
  remembered.
- Narrows the library to what you type, from a box that opens in the top tray
  and closes again, which restores everything. An album that matches keeps all
  of its tracks, so it reads the way it always does; the track the phrase hit
  is highlighted and its row flashes a couple of times to take the eye to it.
  Pressing Return asks the same phrase again, which is how to get back to what
  it found after moving off it. The whole library is read on every keystroke
  rather than through an index, which is measured at under half a millisecond
  and so is faster than an index that could hold the wrong text.
- Shows each album's cover beside it, taken from a file next to the music or
  from the picture inside the audio itself, then kept so it is read once. An
  album with neither keeps a plain square rather than a gap.
- Offers to look a cover up for an album, from the right click menu and only
  from there. It is meant for an album whose own files carry none; it is
  offered for any album, so it will also replace one you would rather not
  keep, since a chosen picture is preferred to whatever sits beside the music.
  The chooser shows every picture MusicBrainz and the Cover Art Archive have
  for that album, each labelled with the release it belongs to; it keeps
  whichever is picked. That picture then outlives a restart and a rescan, since
  it has no file beside the music to be checked against. It is one of the two
  things Stellody does that reach outside the machine and it happens only when
  asked.
- Plays a track chosen by double click, by Return or from the right click
  menu, then works through the album on its own.
- Offers previous, play and pause, stop and next, both on the toolbar across
  the top and on that menu, with the library highlight following whatever is
  playing. Back returns
  to the beginning of the track in hand and waits there; pressing it again from
  there goes to the track before, waiting at its beginning too.
- Carries volume, mute, shuffle and repeat, each remembered between sessions.
  Shuffle leads its scattered run with the track already playing, so next
  reaches the whole of the rest of the album. Repeat plays the album again
  rather than the track, scattering it afresh each time round when shuffle is
  on.
- Draws the track's own waveform along the bottom, with a line marking where
  playback has reached and the time either side of it. The shape builds from
  the left as the file is read, so a picture is there at once rather than after
  the whole file has been decoded. A track that is merely highlighted draws its
  shape too, so you can see what a track looks like before deciding to play it;
  what is playing takes the bar back the moment there is something playing.
  Clicking anywhere along it moves there. The figure is corrected for the
  buffer the engine runs ahead by, so it follows what is audible rather than
  what has been decoded. A file's shape is measured once, kept and shared by
  every track a cue sheet album cuts from it.
- Reports damaged metadata instead of silently working around it, so you can
  repair it in a tagger of your choosing.
- Reaches everything from the keyboard, in the order the window is drawn.
- Opens at the size it was left at, maximised again if that is how it was left.
  A size is clamped to the screen actually attached, so a window sized for a
  monitor that has since gone opens somewhere you can reach it.
- Runs in the notification area and can start there. The setup program offers to
  start Stellody when you sign in, which brings it up there rather than over
  whatever Windows has just finished drawing. Opening Stellody again
  while it is already running brings that window back rather than starting a
  second copy.
- Asks what the window's close button should mean the first time you press it,
  offering the notification area or a full quit; staying is the default and
  the answer can be remembered so it stops asking. "Ask again when I close"
  takes that answer back, from the File menu or from the notification area's
  own menu, since the window is hidden exactly when you want the question
  again. A fresh install or a reinstall forgets it too.
- Ends when you tell it to. Quit, on that menu or on the close prompt, closes
  the application rather than leaving it running with no window.
- Offers to buy the author a drink, which opens a donation page in your
  browser.

Stellody is early. Ratings, play counts, an equalizer, gapless transitions and
accepting the repairs the health report describes are not built; `PLAN.md`
lists what is still to come and what is deliberately excluded.
Where a control for one of those is already on screen it is disabled and says
so.

## What it deliberately does not do

- **It never writes to your music files.** This is enforced by a structural
  test, not by good intentions.
- It sends nothing to the internet on its own. No scrobbling, no telemetry and
  no update check. Two things reach outward and both wait to be asked: the
  donation button hands a link to your browser, which then does the asking;
  "Find cover art online..." on an album's right click menu opens the chooser
  described above. Starting Stellody, scanning a library and playing it open no
  connection at all. A structural test holds that in place rather than a
  promise: exactly one module may hold the machinery for a connection and only
  the composition root may name it.
- It does not encrypt anything at rest. The store holds library metadata, not
  secrets.
- It keeps a plain-text account of its own comings and goings at
  `%TEMP%\stellody-diary.log`: when a window was shown, what asked for it and
  how a shutdown went. It exists because a window arriving unbidden is
  otherwise impossible to trace after the fact. It records no music, no
  library contents and no personal data, it is never sent anywhere and you
  may delete it at any time.

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

Dual licensed. The model, meaning the domain, application, infrastructure and
shared layers together with `main.py`, the build scripts and the tests, is
under GPL-3.0. The user interface layer is under LGPL-3.0, to align with Qt.
See `LICENSE` for the mapping.
