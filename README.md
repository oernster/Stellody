# <img width="128" height="128" alt="application-icon" src="https://github.com/user-attachments/assets/856669d1-6207-4f38-8ed6-816c6b05a40f" /> Stellody

**A free music player for the collection already on your computer.**

*Stellar* and *melody*, run together. The icon says the same thing: a note over
a galaxy, wearing a planet's ring.

No account, no subscription, no adverts and nothing sent anywhere. Point it at
your music folder and it does the rest.

Above all, it never changes a single one of your files.

[Download for Windows](https://github.com/oernster/stellody/releases/latest/download/StellodySetup.exe)
&middot;
[stellody.co.uk](https://stellody.co.uk/)

## Why it exists

Someone spent years turning a shelf of CDs into files: ripping each one,
checking the track names, fixing the artist on the compilations, finding the
right cover art. Then a well known music player reached into those files and
rewrote the information stored inside them. It damaged 33 albums. The music
still played; the careful work around it was gone.

Stellody is built on one rule that everything else follows from: your files are
opened to be read and never to be changed. Where it finds something muddled in
the way an album is labelled, it tells you plainly then leaves the file exactly
as it found it.

That is not a promise on a page. It is checked every time the program is built;
if it ever stopped being true the build would fail.

## What you get

- **A wall of album covers**, else a plain list, whichever suits you. Click a
  cover and the album opens underneath without losing your place. Switching
  between the two lands where you were, so whatever is playing is picked out
  either way. In the list, one press on the Title heading opens every album at
  once; another closes them.
- **Search that narrows as you type**, however many thousands of songs you
  have. The album stays whole around whatever you were looking for.
- **Albums that flow.** Records made to run straight through play that way,
  with no silence dropped in where the artist never put one.
- **An equalizer, plus little bars that dance.** Ten sliders from deep bass to
  high treble, with twenty bars along the bottom showing what the music is
  doing. Switched off, the sound reaching your speakers is bit for bit what is
  in the file, for the formats that store it exactly: FLAC, WAV, AIFF and the
  lossless ALAC inside an M4A.
- **The shape of each song** drawn along the bottom, so you can see the quiet
  parts and the loud ones. Click anywhere on it to jump there.
- **Stars and play counts.** Rate a song, rate the album separately, then read
  down a record to see what you keep coming back to. Only a song played all the
  way through counts.
- **Album art found for you**, from what your files already carry. For an album
  with none, ask Stellody to look then pick from what it finds. It never
  guesses.
- **Your messy collection, sorted out.** An album saved as one long file, a box
  set spread over several folders, a bonus disc with no number in its name: all
  of it comes out as one album where there should be one album.
- **A scan that says what it found.** Add music, press Rescan and you get the
  new albums by name, the new tracks counted and your library's totals, rather
  than a line that disappears while you are looking elsewhere.
- **Say what an album really is.** Where a tag is wrong rather than merely
  muddled, state the artist, the title, the year or the genre yourself and
  Stellody remembers it. Genres come from a settled list of eighteen headings
  with their styles under them, so the same music cannot end up under three
  spellings of one word. Your files are read for this and never written.
- **Show me only the folk.** Narrow the wall of covers to the genres you ask
  for, including the albums that state none at all, then clear it in one press.
  Every tick widens what is shown, so asking for two genres shows both.
- **The videos that came with the album.** A bonus video sits in the album it
  belongs to, plays from the same press as any song and draws its picture at
  the size it was made; fill the window when you want it larger.
- **Corrections you can keep.** Where an album's labelling is muddled, Stellody
  works out what it should be and shows you the tidy version. Now you can tell
  it to keep that answer, all of it at once or one album at a time, so the same
  list of problems stops greeting you at every start. Changed your mind? One
  press puts it back. Your files are untouched either way.
- **A guide to the window itself.** Help then Guide names every button on both
  trays beside the picture the window actually draws, so nothing has to be
  recognised from a description. Under that sit the four rules no single screen
  can state for itself: your files are only ever read, folders group while tags
  name, a correction differs from a stated tag, ratings follow the album rather
  than the file.
- **Everything reachable from the keyboard.** It can also wait quietly by the
  clock rather than filling your screen.

The [features page](https://stellody.co.uk/features.html) has the lot.

## Before you download

- **It plays FLAC, MP3, Ogg, Opus, WAV, AIFF and M4A.** Not WMA, Monkey's Audio,
  WavPack, Musepack or DSD. Anything it cannot decode is now named in the health
  report rather than passed over, so a missing album says so instead of simply
  not appearing. An M4A carries either AAC or ALAC and the difference matters:
  the lossy one is played without ever being called bit perfect, while ALAC
  states the depth it stores and can be. A bonus video that came with an album
  plays as well, from the same MP4 container under a `.m4v` name.
- **Windows only.** Mac and Linux are planned.
- **It is a player, nothing more.** It does not stream, does not copy your CDs,
  does not sync to a phone and will not reorganise your files by rewriting
  them.
- **It is still young.** It tidies muddled labelling in its own view and lets
  you keep that, though it will never rewrite the files themselves: that is the
  whole point rather than a limitation. A control that cannot do anything just
  now is greyed out rather than left to disappoint you.

## Your privacy

Stellody does not know who you are. No account, no profile, no newsletter and
no record kept anywhere of what you listen to. Your music plays perfectly well
with the internet switched off.

Three things reach outside your computer at all, so here are all three:

- **Looking for album art**, only ever when you ask, one album at a time.
- **Checking for a new version**, once a day. It sends nothing about you or
  your music, not even which version you have: the request names the program
  and asks for one public page. Then it stays quiet unless there is something
  new.
- **The donation button**, which hands an address to your web browser. Stellody
  itself connects to nothing. It is one button on the bottom strip and the only
  place money is mentioned; its tooltip offers to buy the author a drink, which
  is the whole of the asking. Nothing prompts you beyond that button being
  there, nothing reminds you later and nothing about the program changes if you
  never press it.

It does not encrypt anything at rest: the store holds notes about your library,
not secrets. It also keeps a plain-text account of its own comings and goings
at `%TEMP%\stellody-diary.log`, which records no music and no personal data, is
never sent anywhere and can be deleted whenever you like.

## Installing

Download the setup program and run it. It installs just for you, so Windows
will not ask for an administrator password. Running it again later is how you
update, repair or remove it.

---

# For developers

Everything above is the product. What follows is the code.

## Stack

| Concern | Choice |
|---|---|
| Language | Python 3.13 |
| Interface | PySide6 |
| Tags | mutagen |
| Decode | soundfile, plus PyAV for M4A |
| Output | sounddevice, on WASAPI |
| Buffers | numpy |
| Store | SQLite |

`ARCHITECTURE.md` states the invariants first, each linked to the test that
enforces it. `PLAN.md` holds the open work plus what is deliberately excluded.
`TECH_DEBT.md` says what is still open internally, what is deliberately left
and what only looks like debt.

## Running from source

```
python -m pip install -r requirements-dev.txt
python main.py
```

**The runtime is pinned; the tools are not.** `requirements.txt` names exact
versions, because a build of one commit has to be the same build whenever it is
made. `requirements-dev.txt` reads it before adding black, flake8, ruff, pytest
and Nuitka, which keep their floors, since a linter moving forward changes the
checks rather than what is shipped. Upgrading a pinned package therefore fails
the suite until the pin is moved to match, naming the package and both versions;
that is the guard working rather than a fault.

## Tests

```
.\gate.ps1
```

That runs the formatter, both linters and the suite against the project's own
virtual environment, reading each exit code rather than its output. Running
`python -m pytest` directly works too, provided it is the venv's Python: a
test refuses the run otherwise: the checks passing in one environment while
the application runs in another is a fault this project has actually had.

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

## The website

`docs/` is the site, served by GitHub Pages at
[stellody.co.uk](https://stellody.co.uk/), which is the canonical host. Version
tokens in it are stamped from `VERSION` by `stamp_version.py`, which both build
scripts call, so the site is never hand-versioned.

The same pages are also served at `stellody.com`, out of the
[stellody-website](https://github.com/oernster/stellody-website) repository
under `public/`. **That mirror keeps itself up to date and needs nothing from
you.** Pushing a change to `docs/` runs `.github/workflows/mirror-site.yml`,
which carries it across, pushes it then asks Render to deploy it. Commit here
and both hosts follow.

**The deploy is asked for rather than inferred, deliberately.** Render's own
Auto-Deploy is set to On Commit and has been throughout, yet every deploy since
July was triggered by hand or by a settings change: the link stopped delivering
push events months ago with nothing anywhere saying so. The workflow already
knows a deploy is wanted, so it says so outright, through a deploy hook held as
`RENDER_DEPLOY_HOOK`. Without that secret the mirror still updates while
stellody.com waits; the run then logs a warning saying exactly that.

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

The workflow needs one secret, `MIRROR_TOKEN`: a fine-grained personal access
token scoped to `oernster/stellody-website` alone, with Contents set to read
and write.

## Licence

Dual licensed. The model, meaning the domain, application, infrastructure and
shared layers together with `main.py`, the build scripts and the tests, is
under GPL-3.0. The user interface layer is under LGPL-3.0, to align with Qt.
See `LICENSE` for the mapping.

A packaged build bundles FFmpeg through PyAV, to decode M4A. The FFmpeg
libraries themselves are built LGPL-3.0-or-later, verified from the licence
string the build reports rather than from its documentation. That build also
links libx264 and libx265, which are GPL-2.0-or-later, so the packaged
application as a whole is distributed as a GPL-3.0 work. Nothing here encodes
video; those two arrive as dependencies of the shared FFmpeg build.
