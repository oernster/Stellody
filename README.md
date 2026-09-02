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
  cover and the album opens underneath without losing your place.
- **Search that narrows as you type**, however many thousands of songs you
  have. The album stays whole around whatever you were looking for.
- **Albums that flow.** Records made to run straight through play that way,
  with no silence dropped in where the artist never put one.
- **An equalizer, plus little bars that dance.** Ten sliders from deep bass to
  high treble, with twenty bars along the bottom showing what the music is
  doing. Switched off, the sound reaching your speakers is bit for bit what is
  in the file, for the formats that store it exactly: FLAC, WAV and AIFF.
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
- **Corrections you can keep.** Where an album's labelling is muddled, Stellody
  works out what it should be and shows you the tidy version. Now you can tell
  it to keep that answer, all of it at once or one album at a time, so the same
  list of problems stops greeting you at every start. Changed your mind? One
  press puts it back. Your files are untouched either way.
- **Everything reachable from the keyboard.** It can also wait quietly by the
  clock rather than filling your screen.

The [features page](https://stellody.co.uk/features.html) has the lot.

## Before you download

- **It plays FLAC, MP3, Ogg, Opus, WAV and AIFF.** Not M4A or WMA yet, so if your
  collection is in one of those, Stellody will not find it. This is the one
  thing worth checking first. The remaining formats are being worked on.
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
- **Checking for a new version**, once a day. It sends nothing whatever when it
  asks, not even which version you have, then stays quiet unless there is
  something new.
- **The donation button**, which hands an address to your web browser. Stellody
  itself connects to nothing. It is one button on the bottom strip and the only
  place money is mentioned: nothing prompts you, nothing reminds you later and
  nothing about the program changes if you never press it.

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
| Decode | soundfile |
| Output | sounddevice, on WASAPI |
| Buffers | numpy |
| Store | SQLite |

`ARCHITECTURE.md` states the invariants first, each linked to the test that
enforces it. `PLAN.md` holds the open work plus what is deliberately excluded.

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
