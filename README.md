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
`PLAN.md` milestone 3 is the work that widens it and sizes both halves of it.

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
  it has no file beside the music to be checked against. It is one of the ways
  Stellody reaches outside the machine, listed in full below; it is also the
  one that waits longest to be asked, since nothing here goes looking.
- Plays a track chosen by double click, by Return or from the right click
  menu, then works through the album on its own. An open album carries its own
  play button in its header, which starts that album from its first track and
  wears the pause face while something is playing, so it says the same thing
  the toolbar's does rather than offering to start what is already going.
- Offers previous, play and pause, stop and next, both on the toolbar across
  the top and on that menu, with the library highlight following whatever is
  playing. Back returns
  to the beginning of the track in hand and waits there; pressing it again from
  there goes to the track before, waiting at its beginning too.
- Carries volume, mute, shuffle and repeat, each remembered between sessions.
  Shuffle leads its scattered run with the track already playing, so next
  reaches the whole of the rest of the album. Repeat has three states rather
  than two, stepped through by pressing it: off, the album again, then the one
  track held on its own. Every switch on the bottom strip shows the state a
  press would move it to rather than the one it is holding, which is the rule
  the tooltips and the mute switch already followed: repeat shows the plain
  wheel while it is off, the numbered wheel while the album repeats and the
  wheel crossed out while one track is held. The album scatters itself afresh
  each time round when shuffle is on. A held track replays when it ends;
  pressing next still moves on, since asking to move on is not a state the
  switch is in.
- Runs one track into the next without a gap, which is what an album
  mixed to play through needs. The following track is opened and decoding
  while the current one is still playing, then the device is handed one
  unbroken run of audio rather than being stopped and started between the
  two. A track held on repeat rejoins itself the same way. Where the next
  track needs a different sample rate the device has to be reopened, so
  that one join is honestly gapped rather than joined badly.
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
- Takes a rating out of five stars for any track, from a rectangle at the right
  of the position bar. It counts a track each time it plays out. The stars are
  about whichever track you have picked out, so a track you have never played
  can be rated; so can one you point at while something else is playing.
  An album carries a rating of its own, set from the stars in its own header
  under the artist's name and labelled there so it cannot be mistaken for the
  track's: a record with one poor track on it is not a poor record, so neither
  rating is worked out from the other.
  Pressing the star a track already sits on takes the rating back,
  since nought is the absence of a rating rather than a sixth one. Reaching the
  end is what counts as a play, so skipping through an album counts nothing.
  A track's count sits on the track's own row in the album's list, beside the
  rest of its detail, so a record can be read down for the tracks you keep
  coming back to. A track that has never played out says nothing there rather
  than nought, since a column of noughts says only that the library is new.
  Neither ever reaches your files: both are kept in Stellody's own store
  against the album's identity rather than against a path, so renaming a folder
  does not lose them.
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
  offering the notification area or a full quit; staying is the one it leads
  with and the answer can be remembered so it stops asking. Waving that
  question away decides nothing: the cross on it, else Escape, takes the whole
  press back, so the window neither leaves nor hides and nothing is
  remembered. "Ask again when I close" takes a remembered answer back, from
  the File menu or from the notification area's own menu, since the window is
  hidden exactly when you want the question again. A fresh install or a
  reinstall forgets it too.
- Ends when you tell it to. Quit, on that menu or on the close prompt, closes
  the application rather than leaving it running with no window.
- Offers to buy the author a drink, which opens a donation page in your
  browser.
- Gathers what is worth reading behind one Help button at the right of the top
  tray, which drops a menu carrying About and Check for updates. The menu bar's
  Help menu carries both as well, along with the library health report and the
  two licences.
- Says when a newer Stellody has been published, from either of those. It
  offers the file for your own machine, a way to skip that version for good,
  else Later. Asked from the menu
  it answers whichever way it turns out, including that it could not reach
  GitHub; left to itself it speaks only when there is something to offer.

Stellody is early. An equalizer and accepting the repairs the health report
describes are not built; `PLAN.md` lists what is still to come and what is
deliberately excluded.
Where a control for one of those is already on screen it is disabled and says
so.

## What it deliberately does not do

- **It never writes to your music files.** This is enforced by a structural
  test, not by good intentions.
- **It sends nothing about you or your library anywhere.** No scrobbling, no
  telemetry, no account and no identifier of any kind. Three things reach
  outward and each is named here rather than left to be discovered. Two of them
  wait to be asked: the donation button hands a link to your browser, which then
  does the asking; "Find cover art online..." on an album's right click menu
  opens the chooser described above. The third speaks first: about three seconds
  after the window opens, then once a day after that, Stellody asks GitHub
  whether a newer Stellody has been published. That request carries nothing at
  all, not even which version you are running; it reads one small public
  document and the comparison happens on your machine. It says nothing unless
  there is a newer version; Skip This Version silences it for that release.
  Help then Check for updates asks the same question outright. Scanning a
  library and playing it still open no connection whatever. A structural test
  holds the rest in place rather than a promise: exactly two modules may hold
  the machinery for a connection, each named in that test with what it is for;
  only the composition root may name them.
- It does not encrypt anything at rest. The store holds library metadata, not
  secrets. Alongside your appearance, sort order, view, volume and window size,
  the store also keeps the one release tag you asked not to be told about
  again, if you have skipped one.
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

## The website

`docs/` is the site, served by GitHub Pages at
[stellody.co.uk](https://stellody.co.uk/), which is the canonical host. Version
tokens in it are stamped from `VERSION` by `stamp_version.py`, which both build
scripts call, so the site is never hand-versioned.

The same pages are also served at `stellody.com`, out of the
[stellody-website](https://github.com/oernster/stellody-website) repository
under `public/`. **That mirror keeps itself up to date and needs nothing from
you.** Pushing a change to `docs/` runs `.github/workflows/mirror-site.yml`,
which carries it across and pushes it; that push in turn starts Render's
deploy. Commit here and both hosts follow.

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

The workflow needs one secret, `MIRROR_TOKEN`: a fine-grained personal access
token scoped to `oernster/stellody-website` alone, with Contents set to read
and write.

## Licence

Dual licensed. The model, meaning the domain, application, infrastructure and
shared layers together with `main.py`, the build scripts and the tests, is
under GPL-3.0. The user interface layer is under LGPL-3.0, to align with Qt.
See `LICENSE` for the mapping.
